import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def _():
    from __future__ import annotations

    import hashlib
    import json
    import shutil
    import tempfile
    import time
    from dataclasses import dataclass
    from pathlib import Path


    # ============================================================
    # CONFIG
    # ============================================================


    @dataclass
    class DedupeConfig:
        # Input/output
        jsonl_path: str = "lichess_db_eval.jsonl"
        output_path: str = "lichess_db_eval_deduped.jsonl"
        tempdir: str | None = "tempfile"

        # Dedupe behavior
        fen_field: str = "fen"  # e.g. "fen" or "position.fen"
        buckets: int = 4096  # increase if a bucket gets too large
        keep: str = "first"  # "first" or "last"

        # Parsing / hashing
        encoding: str = "utf-8"
        errors: str = "replace"
        hash_name: str = "blake2b"  # blake2b, sha256, md5
        digest_bytes: int = 16  # only used for blake2b

        # Optional behavior
        keep_empty: bool = False
        keep_temp: bool = False
        progress_every: int = 1_000_000

        # Robustness
        skip_bad_json: bool = True
        skip_missing_fen: bool = True


    # ============================================================
    # HELPERS
    # ============================================================


    def make_hasher(name: str, digest_bytes: int):
        if name == "blake2b":
            return lambda data: hashlib.blake2b(
                data, digest_size=digest_bytes
            ).digest()
        if name == "sha256":
            return lambda data: hashlib.sha256(data).digest()
        if name == "md5":
            return lambda data: hashlib.md5(data).digest()
        raise ValueError(f"Unsupported hash: {name}")


    def get_nested_field(obj, field_path: str):
        cur = obj
        for part in field_path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
        return cur


    def choose_bucket_id(key: str, buckets: int, hash_bytes_func) -> int:
        digest = hash_bytes_func(key.encode("utf-8", errors="surrogatepass"))
        return int.from_bytes(digest[:8], "little", signed=False) % buckets


    def ensure_parent_dir(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)


    # ============================================================
    # PASS 1: PARTITION INPUT INTO BUCKETS
    # ============================================================


    def partition_jsonl(cfg: DedupeConfig, bucket_dir: Path, hash_bytes_func):
        bucket_paths = [
            bucket_dir / f"bucket_{i:05d}.jsonl" for i in range(cfg.buckets)
        ]
        bucket_files = [
            open(p, "w", encoding=cfg.encoding, newline="\n") for p in bucket_paths
        ]

        total_lines = 0
        written_lines = 0
        skipped_empty = 0
        skipped_bad_json = 0
        skipped_missing_fen = 0

        start = time.time()

        try:
            with open(
                cfg.jsonl_path, "r", encoding=cfg.encoding, errors=cfg.errors
            ) as fin:
                for raw_line in fin:
                    total_lines += 1
                    line = raw_line.strip()

                    if not line:
                        skipped_empty += 1
                        if cfg.keep_empty:
                            bucket_files[0].write("\n")
                            written_lines += 1
                        continue

                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        if cfg.skip_bad_json:
                            skipped_bad_json += 1
                            continue
                        raise

                    fen = get_nested_field(obj, cfg.fen_field)
                    if fen is None:
                        if cfg.skip_missing_fen:
                            skipped_missing_fen += 1
                            continue
                        raise KeyError(
                            f"Missing field '{cfg.fen_field}' in record: {line[:300]}"
                        )

                    fen = str(fen)
                    bucket_id = choose_bucket_id(fen, cfg.buckets, hash_bytes_func)
                    bucket_files[bucket_id].write(line + "\n")
                    written_lines += 1

                    if (
                        cfg.progress_every
                        and total_lines % cfg.progress_every == 0
                    ):
                        elapsed = time.time() - start
                        rate = total_lines / elapsed if elapsed > 0 else 0
                        print(
                            f"[partition] lines={total_lines:,} "
                            f"written={written_lines:,} "
                            f"skipped_empty={skipped_empty:,} "
                            f"skipped_bad_json={skipped_bad_json:,} "
                            f"skipped_missing_fen={skipped_missing_fen:,} "
                            f"rate={rate:,.0f} lines/s"
                        )
        finally:
            for f in bucket_files:
                f.close()

        elapsed = time.time() - start
        return {
            "total_lines": total_lines,
            "written_lines": written_lines,
            "skipped_empty": skipped_empty,
            "skipped_bad_json": skipped_bad_json,
            "skipped_missing_fen": skipped_missing_fen,
            "seconds": elapsed,
        }


    # ============================================================
    # PASS 2: DEDUPE EACH BUCKET
    # ============================================================


    def dedupe_bucket_file(bucket_path: Path, fout, cfg: DedupeConfig):
        """
        Deduplicate one bucket by FEN.

        keep="first": keep the first record encountered for each FEN in this bucket
        keep="last":  keep the last record encountered for each FEN in this bucket
        """
        input_lines = 0
        unique_lines = 0

        if cfg.keep not in {"first", "last"}:
            raise ValueError("cfg.keep must be 'first' or 'last'")

        if cfg.keep == "first":
            seen_fens = set()

            with open(
                bucket_path, "r", encoding=cfg.encoding, errors=cfg.errors
            ) as f:
                for raw_line in f:
                    input_lines += 1
                    line = raw_line.strip()
                    if not line:
                        continue

                    obj = json.loads(line)
                    fen = get_nested_field(obj, cfg.fen_field)
                    if fen is None:
                        continue

                    fen = str(fen)
                    if fen in seen_fens:
                        continue

                    seen_fens.add(fen)
                    fout.write(line + "\n")
                    unique_lines += 1

        else:  # keep == "last"
            latest_by_fen = {}

            with open(
                bucket_path, "r", encoding=cfg.encoding, errors=cfg.errors
            ) as f:
                for raw_line in f:
                    input_lines += 1
                    line = raw_line.strip()
                    if not line:
                        continue

                    obj = json.loads(line)
                    fen = get_nested_field(obj, cfg.fen_field)
                    if fen is None:
                        continue

                    fen = str(fen)
                    latest_by_fen[fen] = line

            for line in latest_by_fen.values():
                fout.write(line + "\n")
                unique_lines += 1

        return input_lines, unique_lines


    def process_buckets(cfg: DedupeConfig, bucket_dir: Path):
        bucket_paths = sorted(bucket_dir.glob("bucket_*.jsonl"))
        total_input = 0
        total_unique = 0

        start = time.time()

        with open(
            cfg.output_path, "w", encoding=cfg.encoding, newline="\n"
        ) as fout:
            for idx, bucket_path in enumerate(bucket_paths, start=1):
                in_count, unique_count = dedupe_bucket_file(bucket_path, fout, cfg)
                total_input += in_count
                total_unique += unique_count

                print(
                    f"[dedupe] bucket={idx}/{len(bucket_paths)} "
                    f"input={in_count:,} unique={unique_count:,}"
                )

        elapsed = time.time() - start
        return {
            "bucket_count": len(bucket_paths),
            "bucket_input_lines": total_input,
            "unique_records": total_unique,
            "removed_duplicates": total_input - total_unique,
            "seconds": elapsed,
        }


    # ============================================================
    # MAIN RUNNER
    # ============================================================


    def run_jsonl_fen_dedupe(cfg: DedupeConfig):
        input_path = Path(cfg.jsonl_path)
        output_path = Path(cfg.output_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if cfg.buckets < 2:
            raise ValueError("cfg.buckets must be at least 2")

        ensure_parent_dir(output_path)

        hash_bytes_func = make_hasher(cfg.hash_name, cfg.digest_bytes)

        if cfg.tempdir:
            temp_root = Path(cfg.tempdir)
            temp_root.mkdir(parents=True, exist_ok=True)
            work_dir = Path(
                tempfile.mkdtemp(prefix="fen_jsonl_dedupe_", dir=temp_root)
            )
        else:
            work_dir = Path(tempfile.mkdtemp(prefix="fen_jsonl_dedupe_"))

        bucket_dir = work_dir / "buckets"
        bucket_dir.mkdir(parents=True, exist_ok=True)

        print(f"[info] input={input_path}")
        print(f"[info] output={output_path}")
        print(f"[info] temp_workdir={work_dir}")
        print(f"[info] fen_field={cfg.fen_field}")
        print(f"[info] buckets={cfg.buckets}")
        print(f"[info] keep={cfg.keep}")
        print(f"[info] hash={cfg.hash_name}")

        try:
            part_stats = partition_jsonl(cfg, bucket_dir, hash_bytes_func)
            print(f"[done-partition] {part_stats}")

            dedupe_stats = process_buckets(cfg, bucket_dir)
            print(f"[done-dedupe] {dedupe_stats}")

            return {
                "partition": part_stats,
                "dedupe": dedupe_stats,
                "temp_dir": str(work_dir),
                "output_path": str(output_path),
            }

        finally:
            if cfg.keep_temp:
                print(f"[info] keeping temp dir: {work_dir}")
            else:
                shutil.rmtree(work_dir, ignore_errors=True)


    # ============================================================
    # EXAMPLE USAGE IN MARIMO OR NOTEBOOK
    # ============================================================

    cfg = DedupeConfig(
        jsonl_path="lichess_db_eval.jsonl",
        output_path="lichess_db_eval_deduped.jsonl",
        tempdir="tempfile",  # set to None to use system temp
        fen_field="fen",  # or e.g. "position.fen"
        buckets=4096,
        keep="first",  # or "last"
        keep_temp=False,
    )

    # Uncomment to run:
    result = run_jsonl_fen_dedupe(cfg)
    result
    return


if __name__ == "__main__":
    app.run()
