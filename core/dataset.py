import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # `core/dataset.py` — Chess pair dataset + corruption dataloader

    Defines:

    - `FEN_PIECES`, `PIECE_TO_CHANNEL` — channel-ordering constants matching the spec.
    - `fen_to_tensor` / `tensor_to_fen` — 8×8×18 board representation per the spec
      (channels 0–11 piece occupancy WPNBRQK then BPNBRQK, 12 STM, 13–16 castling, 17 EP).
    - `ChessPairDataset` — reads the **precomputed** CSV (5 columns: `problem_fen`,
      `trace_fen`, `corrupt_shuffle`, `corrupt_legal_move`, `corrupt_piece_swap`) and on
      `__getitem__` selects one corruption column according to a configurable mixture.
    - `make_dataloader` — convenience builder.
    - `train_val_indices` — deterministic 95/5 split via index hashing (seed 42).

    Corruption-column mapping (fixed; matches the precompute):
    col 3 = `corrupt_shuffle`, col 4 = `corrupt_legal_move`, col 5 = `corrupt_piece_swap`.

    Mixture presets:

    - `EASY_MIX = (0.30, 0.40, 0.30)` — stages 1–3.
    - `HARD_MIX = (0.20, 0.60, 0.20)` — stage 4.

    This notebook is **definition-only** so it can be imported by training
    notebooks. Sanity cells at the bottom run a small forward pass and print
    shapes; they never write files or train.
    """)
    return


@app.cell
def _():
    import hashlib
    import os

    import numpy as np
    import pandas as pd
    import torch
    from torch.utils.data import DataLoader, Dataset

    return DataLoader, Dataset, hashlib, np, os, pd, torch


@app.cell
def _(mo):
    mo.md("""
    ## Constants
    """)
    return


@app.cell
def _():
    # Path to the precomputed corruption CSV produced by the precompute script.
    DATA_CSV_PATH = "/workspace/core/precomputed_corruptions.csv"

    # Column names in the precomputed CSV. Order is (clean_problem, clean_trace,
    # corruption_slot_3, corruption_slot_4, corruption_slot_5).
    COL_PROBLEM   = "problem_fen"
    COL_TRACE     = "trace_fen"
    COL_CORRUPT_3 = "corrupt_shuffle"      # cf. EASY[0] / HARD[0]
    COL_CORRUPT_4 = "corrupt_legal_move"   # cf. EASY[1] / HARD[1]
    COL_CORRUPT_5 = "corrupt_piece_swap"   # cf. EASY[2] / HARD[2]

    # Corruption-mix presets. Indices align with (col 3, col 4, col 5).
    EASY_MIX = (0.30, 0.40, 0.30)  # stages 1-3
    HARD_MIX = (0.20, 0.60, 0.20)  # stage 4

    # Determinism
    SEED = 42
    return (
        COL_CORRUPT_3,
        COL_CORRUPT_4,
        COL_CORRUPT_5,
        COL_PROBLEM,
        COL_TRACE,
        DATA_CSV_PATH,
        EASY_MIX,
        HARD_MIX,
        SEED,
    )


@app.cell
def _():
    # Channel ordering: white pieces 0..5, black pieces 6..11.
    # Order within each color is P, N, B, R, Q, K (matches python-chess piece-symbol order).
    FEN_PIECES = ["P", "N", "B", "R", "Q", "K", "p", "n", "b", "r", "q", "k"]
    PIECE_TO_CHANNEL = {p: i for i, p in enumerate(FEN_PIECES)}
    CHANNEL_TO_PIECE = {i: p for p, i in PIECE_TO_CHANNEL.items()}

    # Channel layout indices (referenced by fen_to_tensor / tensor_to_fen).
    CH_STM        = 12
    CH_CASTLE_WK  = 13
    CH_CASTLE_WQ  = 14
    CH_CASTLE_BK  = 15
    CH_CASTLE_BQ  = 16
    CH_EP         = 17
    NUM_CHANNELS  = 18
    return (
        CHANNEL_TO_PIECE,
        CH_CASTLE_BK,
        CH_CASTLE_BQ,
        CH_CASTLE_WK,
        CH_CASTLE_WQ,
        CH_EP,
        CH_STM,
        NUM_CHANNELS,
        PIECE_TO_CHANNEL,
    )


@app.cell
def _(mo):
    mo.md("""
    ## FEN ↔ tensor conversion
    """)
    return


@app.cell
def _(
    CHANNEL_TO_PIECE,
    CH_CASTLE_BK,
    CH_CASTLE_BQ,
    CH_CASTLE_WK,
    CH_CASTLE_WQ,
    CH_EP,
    CH_STM,
    NUM_CHANNELS,
    PIECE_TO_CHANNEL,
    np,
    torch,
):
    def fen_to_tensor(fen: str) -> torch.Tensor:
        """
        Convert a FEN string to an (18, 8, 8) float tensor per the spec.

        Layout (rank 0 = rank 8 of the board, file 0 = file a). This means
        tensor[c, 0, 0] corresponds to square a8, tensor[c, 7, 7] to h1, which
        matches how FEN's piece-placement field is laid out (rank 8 first).

        Channels:
          0..11 : piece occupancy, order P N B R Q K p n b r q k
          12    : side-to-move (1.0 white-to-move broadcast, else 0.0)
          13..16: castling rights WK, WQ, BK, BQ (broadcast)
          17    : en-passant target (single 1.0 cell at target square)
        """
        board = np.zeros((NUM_CHANNELS, 8, 8), dtype=np.float32)
        parts = fen.split()
        # FEN may legally lack the en-passant / clock fields in some weird inputs;
        # be defensive but the precomputed CSV is python-chess-emitted so it's fine.
        placement = parts[0]
        stm       = parts[1] if len(parts) > 1 else "w"
        castling  = parts[2] if len(parts) > 2 else "-"
        ep        = parts[3] if len(parts) > 3 else "-"

        # Piece placement.
        for rank_idx, rank_str in enumerate(placement.split("/")):
            file_idx = 0
            for ch in rank_str:
                if ch.isdigit():
                    file_idx += int(ch)
                else:
                    c = PIECE_TO_CHANNEL[ch]
                    board[c, rank_idx, file_idx] = 1.0
                    file_idx += 1

        # Side-to-move.
        if stm == "w":
            board[CH_STM, :, :] = 1.0

        # Castling rights.
        if "K" in castling: board[CH_CASTLE_WK, :, :] = 1.0
        if "Q" in castling: board[CH_CASTLE_WQ, :, :] = 1.0
        if "k" in castling: board[CH_CASTLE_BK, :, :] = 1.0
        if "q" in castling: board[CH_CASTLE_BQ, :, :] = 1.0

        # En-passant target square.
        if ep != "-" and len(ep) == 2:
            file_idx = ord(ep[0]) - ord("a")
            # FEN ranks are 1..8 (rank 8 first in placement); our tensor
            # rank 0 == rank 8, rank 7 == rank 1.
            rank_idx = 8 - int(ep[1])
            if 0 <= file_idx < 8 and 0 <= rank_idx < 8:
                board[CH_EP, rank_idx, file_idx] = 1.0

        return torch.from_numpy(board)


    def tensor_to_fen(t: torch.Tensor) -> str:
        """
        Inverse of `fen_to_tensor` for raw (binary) tensors. Useful for
        sanity checks / debugging only — diffusion outputs need separate
        argmax + legality handling, see inference notebook.
        """
        if t.dim() == 4:
            assert t.shape[0] == 1, "tensor_to_fen expects a single board"
            t = t[0]
        arr = t.detach().cpu().numpy()

        # Piece placement: take argmax over channels 0..11 with an empty option.
        piece = arr[:12]                             # (12, 8, 8)
        max_val = piece.max(axis=0)                  # (8, 8)
        max_idx = piece.argmax(axis=0)               # (8, 8)
        rows = []
        for r in range(8):
            row_str = ""
            empty = 0
            for f in range(8):
                if max_val[r, f] < 0.5:
                    empty += 1
                else:
                    if empty:
                        row_str += str(empty); empty = 0
                    row_str += CHANNEL_TO_PIECE[int(max_idx[r, f])]
            if empty:
                row_str += str(empty)
            rows.append(row_str)
        placement = "/".join(rows)

        stm = "w" if arr[CH_STM, 0, 0] >= 0.5 else "b"

        castling = ""
        if arr[CH_CASTLE_WK, 0, 0] >= 0.5: castling += "K"
        if arr[CH_CASTLE_WQ, 0, 0] >= 0.5: castling += "Q"
        if arr[CH_CASTLE_BK, 0, 0] >= 0.5: castling += "k"
        if arr[CH_CASTLE_BQ, 0, 0] >= 0.5: castling += "q"
        if not castling:
            castling = "-"

        ep_layer = arr[CH_EP]
        if ep_layer.max() >= 0.5:
            r, f = np.unravel_index(ep_layer.argmax(), ep_layer.shape)
            ep = chr(ord("a") + int(f)) + str(8 - int(r))
        else:
            ep = "-"

        # Halfmove / fullmove clocks aren't encoded — emit 0 1 placeholders so
        # python-chess can re-parse the result without errors.
        return f"{placement} {stm} {castling} {ep} 0 1"

    return (fen_to_tensor,)


@app.cell
def _(mo):
    mo.md("""
    ## Train / val split (deterministic, seed 42, 95 / 5)
    """)
    return


@app.cell
def _(SEED, hashlib, np):
    def train_val_indices(n: int, val_frac: float = 0.05, seed: int = SEED):
        """
        Hash each row index together with `seed` and use the bottom 32 bits as
        the split key. Returns (train_idx, val_idx) numpy arrays. The split is
        identical across runs and across notebooks for the same n.
        """
        keys = np.empty(n, dtype=np.uint32)
        seed_bytes = seed.to_bytes(8, "little")
        for i in range(n):
            h = hashlib.blake2b(seed_bytes + i.to_bytes(8, "little"), digest_size=4).digest()
            keys[i] = int.from_bytes(h, "little")
        # `keys / 2**32` is uniform on [0, 1); rows below val_frac go to val.
        is_val = (keys.astype(np.float64) / (1 << 32)) < val_frac
        all_idx = np.arange(n)
        return all_idx[~is_val], all_idx[is_val]

    return (train_val_indices,)


@app.cell
def _(mo):
    mo.md("""
    ## `ChessPairDataset`

    Reads the precomputed CSV. On `__getitem__` it picks **one** corruption
    column according to `corruption_mix` (a 3-tuple summing to 1.0 over
    `corrupt_shuffle`, `corrupt_legal_move`, `corrupt_piece_swap` in that
    order) and returns three tensors: problem, clean trace, corrupted trace.

    FENs are stored as Python strings until `__getitem__` converts the
    chosen three to tensors — this keeps memory low (~70 MB for FENs vs
    ~3+ GB if we precomputed every tensor).
    """)
    return


@app.cell
def _(
    COL_CORRUPT_3,
    COL_CORRUPT_4,
    COL_CORRUPT_5,
    COL_PROBLEM,
    COL_TRACE,
    DATA_CSV_PATH,
    Dataset,
    EASY_MIX,
    fen_to_tensor,
    np,
    pd,
):
    class ChessPairDataset(Dataset):
        """
        Yields 3-tuples of (problem_board, clean_trace_board, corrupted_trace_board),
        each an (18, 8, 8) float32 tensor.

        Args:
            csv_path:        path to precomputed CSV (5 columns).
            corruption_mix:  (p_shuffle, p_legal, p_swap), must sum to ~1.0.
                             Indices map to (corrupt_shuffle, corrupt_legal_move,
                             corrupt_piece_swap) in that fixed order.
            indices:         optional explicit row indices (post-dedupe) to use,
                             for train/val split. None = all rows.
            seed:            base seed for the per-worker corruption-choice RNG.
        """

        def __init__(
            self,
            csv_path: str = DATA_CSV_PATH,
            corruption_mix=EASY_MIX,
            indices=None,
            seed: int = 42,
            problem_col: str = COL_PROBLEM,
            trace_col: str = COL_TRACE,
            corrupt_cols=(COL_CORRUPT_3, COL_CORRUPT_4, COL_CORRUPT_5),
        ):
            mix = np.asarray(corruption_mix, dtype=np.float64)
            if mix.shape != (3,):
                raise ValueError(f"corruption_mix must be length-3, got shape {mix.shape}")
            if not np.isclose(mix.sum(), 1.0, atol=1e-6):
                raise ValueError(f"corruption_mix must sum to 1.0, got {mix.sum()}")
            if (mix < 0).any():
                raise ValueError(f"corruption_mix entries must be non-negative, got {mix}")

            df = pd.read_csv(csv_path)
            for col in (problem_col, trace_col, *corrupt_cols):
                if col not in df.columns:
                    raise KeyError(f"column {col!r} missing from {csv_path}")

            self._problem  = df[problem_col].to_numpy()
            self._trace    = df[trace_col].to_numpy()
            self._corrupts = [df[c].to_numpy() for c in corrupt_cols]

            if indices is None:
                self._indices = np.arange(len(df), dtype=np.int64)
            else:
                self._indices = np.asarray(indices, dtype=np.int64)

            self._mix = mix
            self._seed = seed

        def __len__(self):
            return len(self._indices)

        def _rng_for(self, idx: int) -> np.random.Generator:
            """
            Per-sample deterministic RNG: same epoch + same idx → same corruption
            choice. This isn't strictly required (sampling is fine to be
            stochastic across epochs) but makes debugging reproducible.
            """
            return np.random.default_rng(self._seed * 1_000_003 + int(idx))

        def __getitem__(self, i: int):
            row = int(self._indices[i])

            # Pick which corruption column to use for this sample.
            rng = self._rng_for(row)
            slot = int(rng.choice(3, p=self._mix))
            corrupt_fen = self._corrupts[slot][row]

            problem_t  = fen_to_tensor(self._problem[row])
            trace_t    = fen_to_tensor(self._trace[row])
            corrupt_t  = fen_to_tensor(corrupt_fen)

            return problem_t, trace_t, corrupt_t

        # Convenience: expose the raw FEN triplet for debugging.
        def get_fens(self, i: int):
            row = int(self._indices[i])
            rng = self._rng_for(row)
            slot = int(rng.choice(3, p=self._mix))
            return (
                self._problem[row],
                self._trace[row],
                self._corrupts[slot][row],
                slot,  # 0=shuffle, 1=legal, 2=swap
            )

    return (ChessPairDataset,)


@app.cell
def _(mo):
    mo.md("""
    ## `make_dataloader` helper
    """)
    return


@app.cell
def _(ChessPairDataset, DataLoader, EASY_MIX, train_val_indices):
    def make_dataloader(
        split: str = "train",
        corruption_mix=EASY_MIX,
        batch_size: int = 64,
        num_workers: int = 4,
        csv_path=None,
        seed: int = 42,
        shuffle=None,
        pin_memory: bool = True,
        drop_last=None,
    ):
        """
        Build a DataLoader for the chess pair dataset.

        split:           'train' or 'val' (95/5 deterministic split).
        corruption_mix:  (p_shuffle, p_legal, p_swap).
        batch_size:      spec recommends starting at 64 on a 4070 Ti Super.
        """
        if split not in ("train", "val"):
            raise ValueError(f"split must be 'train' or 'val', got {split!r}")

        # Build full-size dataset just to discover N, then slice indices.
        kwargs = {} if csv_path is None else {"csv_path": csv_path}
        full = ChessPairDataset(corruption_mix=corruption_mix, seed=seed, **kwargs)
        n = len(full)
        train_idx, val_idx = train_val_indices(n, val_frac=0.05, seed=seed)
        chosen = train_idx if split == "train" else val_idx

        ds = ChessPairDataset(
            corruption_mix=corruption_mix,
            indices=chosen,
            seed=seed,
            **kwargs,
        )

        if shuffle is None:
            shuffle = (split == "train")
        if drop_last is None:
            drop_last = (split == "train")

        return DataLoader(
            ds,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            pin_memory=pin_memory,
            drop_last=drop_last,
            persistent_workers=(num_workers > 0),
        )

    return (make_dataloader,)


@app.cell
def _(mo):
    mo.md("""
    ## Sanity checks

    Cheap forward-pass cells. They run on import (so keep them light: load
    a few rows, build one batch, print shapes). No file writes, no training.
    """)
    return


@app.cell
def _(ChessPairDataset, DATA_CSV_PATH, EASY_MIX, HARD_MIX, os):
    # Only run if the precomputed CSV actually exists. This lets the notebook
    # be imported on machines where the data hasn't been generated yet without
    # blowing up.
    if os.path.exists(DATA_CSV_PATH):
        _ds_easy = ChessPairDataset(corruption_mix=EASY_MIX)
        _ds_hard = ChessPairDataset(corruption_mix=HARD_MIX)
        print(f"[sanity] dataset rows : {len(_ds_easy):,}")
        print(f"[sanity] easy mix     : {EASY_MIX}")
        print(f"[sanity] hard mix     : {HARD_MIX}")

        p, t, c = _ds_easy[0]
        print(f"[sanity] sample 0 shapes: problem {tuple(p.shape)}, "
              f"trace {tuple(t.shape)}, corrupted {tuple(c.shape)}")
        print(f"[sanity] sample 0 dtypes: {p.dtype}, "
              f"sum(problem channels 0..11)={p[:12].sum().item():.0f}")
    else:
        print(f"[sanity] {DATA_CSV_PATH} not found; skipping sanity checks")
    return


@app.cell
def _(ChessPairDataset, DATA_CSV_PATH, EASY_MIX, np, os):
    # Verify the empirical corruption-slot distribution matches the requested mix.
    if os.path.exists(DATA_CSV_PATH):
        _ds = ChessPairDataset(corruption_mix=EASY_MIX)
        slots = np.zeros(3, dtype=np.int64)
        N = min(5000, len(_ds))
        for i in range(N):
            _, _, _, slot = _ds.get_fens(i)
            slots[slot] += 1
        empirical = slots / slots.sum()
        print(f"[sanity] empirical mix over {N} samples: "
              f"{empirical.round(3).tolist()}  (target {EASY_MIX})")
    return


@app.cell
def _(DATA_CSV_PATH, make_dataloader, os):
    # Build one train batch end-to-end to make sure the DataLoader plumbing works.
    if os.path.exists(DATA_CSV_PATH):
        _dl = make_dataloader(
            split="train",
            batch_size=8,
            num_workers=0,   # cheap on import; workers aren't needed for a 1-batch test
        )
        _it = iter(_dl)
        _problem, _trace, _corrupt = next(_it)
        print(f"[sanity] batch shapes : problem {tuple(_problem.shape)}, "
              f"trace {tuple(_trace.shape)}, corrupted {tuple(_corrupt.shape)}")
        print(f"[sanity] batch dtypes : {_problem.dtype}")
    return


if __name__ == "__main__":
    app.run()
