import marimo

__generated_with = "0.9.0"
app = marimo.App(width="medium")


@app.cell
def __(mo):
    mo.md(
        r"""
        # `core/dataset.py` — FEN ↔ tensor helpers, datasets, corruption strategies

        This notebook defines the project's dataloader infrastructure. All other
        notebooks (`training/stage*.py`, `inference/sample.py`) import from here.

        **Defined here:**

        - `fen_to_tensor` / `tensor_to_fen` — round-trip between FEN strings and
          the project's 8×8×18 float tensor representation.
        - Three corruption strategies for negative-trace generation
          (`corrupt_batch_shuffle`, `corrupt_legal_move`, `corrupt_piece_swap`).
        - `BoardDataset` — single-board dataset used by stage 0 (VQ-VAE
          pretraining).
        - `ChessPairDataset` — 3-tuple `(problem, clean_trace, corrupted_trace)`
          dataset used by stages 1–4. The third tuple slot is always materialized
          to keep training-loop signatures uniform across stages; when
          `emit_corruption=False` it is filled with zeros.
        - `make_dataloader` — convenience constructor returning a torch
          `DataLoader` wired up with the custom collate function (which resolves
          the in-batch shuffle corruption strategy).

        **Not done here:** training, checkpointing, plotting (per the project
        convention that `core/` notebooks are definition-only and import-safe).
        """
    )
    return


@app.cell
def __():
    import marimo as mo
    return (mo,)


@app.cell
def __():
    import hashlib
    import random
    from pathlib import Path

    import chess
    import numpy as np
    import pandas as pd
    import torch
    from torch.utils.data import DataLoader, Dataset
    return DataLoader, Dataset, Path, chess, hashlib, np, pd, random, torch


@app.cell
def __(mo):
    mo.md(
        r"""
        ## Constants

        Channel layout (18 total, all in 8×8 grids):

        | Channels | Meaning |
        |----------|---------|
        | 0–5      | White pieces: P, N, B, R, Q, K |
        | 6–11     | Black pieces: P, N, B, R, Q, K |
        | 12       | Side-to-move (1.0 broadcast if white to move, else 0.0) |
        | 13–16    | Castling rights: WK, WQ, BK, BQ (broadcast 1.0 if available) |
        | 17       | En passant target square (1.0 at the target square, 0.0 elsewhere) |

        The empty-square state is implicit: zero on every piece channel. At
        inference time a 13th "empty" logit is added before softmax — that is
        handled in `inference/sample.py`, not here.
        """
    )
    return


@app.cell
def __(Path):
    # Path to the raw CSV. The CSV must have at least the columns named below.
    # Stage 0 uses only PROBLEM_FEN_COL; stages 1–4 use both.
    DATA_CSV_PATH = Path("/mnt/user-data/uploads/dataset_eval.csv")
    PROBLEM_FEN_COL = "Position"
    BEST_MOVE_COL = "Best Move"  # UCI string; trace FEN is derived by applying it.

    SEED = 42
    TRAIN_FRACTION = 0.95  # 95/5 split per spec.
    BOARD_C, BOARD_H, BOARD_W = 18, 8, 8

    # Channel index constants (used by the corruption + tensor helpers).
    PIECE_CHANNELS = 12  # 0..11 are piece occupancy
    STM_CHANNEL = 12
    CASTLING_CHANNELS = (13, 14, 15, 16)  # WK, WQ, BK, BQ
    EP_CHANNEL = 17

    # piece -> channel index. python-chess: PAWN=1, KNIGHT=2, BISHOP=3, ROOK=4, QUEEN=5, KING=6.
    # White uses 0..5, black uses 6..11.
    PIECE_TYPE_OFFSET = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5}
    return (
        BEST_MOVE_COL,
        BOARD_C,
        BOARD_H,
        BOARD_W,
        CASTLING_CHANNELS,
        DATA_CSV_PATH,
        EP_CHANNEL,
        PIECE_CHANNELS,
        PIECE_TYPE_OFFSET,
        PROBLEM_FEN_COL,
        SEED,
        STM_CHANNEL,
        TRAIN_FRACTION,
    )


@app.cell
def __(mo):
    mo.md(
        r"""
        ## FEN ↔ tensor helpers

        `fen_to_tensor` converts a FEN string to an 8×8×18 float tensor.
        `tensor_to_fen` is its inverse and is used by evaluation code in
        `inference/sample.py` to compare predictions to the ground-truth trace
        and to validate legality with `chess.Board(fen).is_valid()`.

        Convention for the rank dimension: rank 8 (top of the board, where black
        starts) is row index 0, rank 1 (where white starts) is row index 7. This
        matches `chess.square_rank` after a `7 - rank` flip and is the standard
        choice in chess CNN papers.
        """
    )
    return


@app.cell
def __(
    BOARD_C,
    BOARD_H,
    BOARD_W,
    CASTLING_CHANNELS,
    EP_CHANNEL,
    PIECE_TYPE_OFFSET,
    STM_CHANNEL,
    chess,
    np,
    torch,
):
    def fen_to_tensor(fen: str) -> torch.Tensor:
        """Convert a FEN string to an (18, 8, 8) float32 tensor.

        Empty squares carry zeros across all 12 piece channels. Metadata
        channels (12–17) are broadcast across the 64 squares for stm and
        castling rights; en passant is a single hot square.
        """
        board = chess.Board(fen)
        t = np.zeros((BOARD_C, BOARD_H, BOARD_W), dtype=np.float32)

        # Piece occupancy.
        for square, piece in board.piece_map().items():
            file_ = chess.square_file(square)         # 0..7, a..h
            rank = chess.square_rank(square)          # 0..7, rank1..rank8
            row = 7 - rank                            # rank8 -> 0, rank1 -> 7
            col = file_
            channel = PIECE_TYPE_OFFSET[piece.piece_type]
            if not piece.color:  # chess.BLACK is False
                channel += 6
            t[channel, row, col] = 1.0

        # Side to move (1.0 if white to move).
        if board.turn == chess.WHITE:
            t[STM_CHANNEL, :, :] = 1.0

        # Castling rights.
        wk, wq, bk, bq = CASTLING_CHANNELS
        if board.has_kingside_castling_rights(chess.WHITE):
            t[wk, :, :] = 1.0
        if board.has_queenside_castling_rights(chess.WHITE):
            t[wq, :, :] = 1.0
        if board.has_kingside_castling_rights(chess.BLACK):
            t[bk, :, :] = 1.0
        if board.has_queenside_castling_rights(chess.BLACK):
            t[bq, :, :] = 1.0

        # En passant target square.
        if board.ep_square is not None:
            ep_file = chess.square_file(board.ep_square)
            ep_rank = chess.square_rank(board.ep_square)
            t[EP_CHANNEL, 7 - ep_rank, ep_file] = 1.0

        return torch.from_numpy(t)
    return (fen_to_tensor,)


@app.cell
def __(
    BOARD_H,
    BOARD_W,
    CASTLING_CHANNELS,
    EP_CHANNEL,
    PIECE_TYPE_OFFSET,
    STM_CHANNEL,
    chess,
    torch,
):
    # Inverse of PIECE_TYPE_OFFSET, plus color: channel -> (piece_type, color).
    _CHANNEL_TO_PIECE = {}
    for _pt, _off in PIECE_TYPE_OFFSET.items():
        _CHANNEL_TO_PIECE[_off] = (_pt, chess.WHITE)
        _CHANNEL_TO_PIECE[_off + 6] = (_pt, chess.BLACK)

    def tensor_to_fen(t: torch.Tensor, threshold: float = 0.5) -> str:
        """Inverse of `fen_to_tensor`. Expects a discrete (18, 8, 8) tensor.

        For continuous tensors (e.g. raw diffusion outputs), discretize first in
        the inference code and pass the result here. This function does NOT do
        the 13-class softmax — it assumes one-hot piece channels and thresholds
        metadata at `threshold`.

        Output FEN uses placeholder halfmove/fullmove clocks ("0 1") since the
        project does not encode them.
        """
        if isinstance(t, torch.Tensor):
            t_np = t.detach().cpu().numpy()
        else:
            t_np = t

        board = chess.Board.empty()

        # Pieces. If multiple piece channels are hot at the same square, take
        # the argmax — this can happen for a not-yet-discretized board, but
        # for a properly discretized one only one channel will be hot.
        for row in range(BOARD_H):
            for col in range(BOARD_W):
                piece_slice = t_np[:12, row, col]
                if piece_slice.max() <= 0.0:
                    continue
                channel = int(piece_slice.argmax())
                piece_type, color = _CHANNEL_TO_PIECE[channel]
                rank = 7 - row
                file_ = col
                square = chess.square(file_, rank)
                board.set_piece_at(square, chess.Piece(piece_type, color))

        # Side to move: take the mean of channel 12 over the 64 squares so that
        # a partially-filled stm channel still resolves cleanly.
        stm_mean = float(t_np[STM_CHANNEL].mean())
        board.turn = chess.WHITE if stm_mean >= threshold else chess.BLACK

        # Castling rights. Build the FEN-style castling string and let
        # python-chess parse it.
        wk, wq, bk, bq = CASTLING_CHANNELS
        castling_chars = []
        if t_np[wk].mean() >= threshold:
            castling_chars.append("K")
        if t_np[wq].mean() >= threshold:
            castling_chars.append("Q")
        if t_np[bk].mean() >= threshold:
            castling_chars.append("k")
        if t_np[bq].mean() >= threshold:
            castling_chars.append("q")
        board.set_castling_fen("".join(castling_chars) if castling_chars else "-")

        # En passant target square.
        ep_plane = t_np[EP_CHANNEL]
        if ep_plane.max() >= threshold:
            row, col = divmod(int(ep_plane.argmax()), BOARD_W)
            rank = 7 - row
            file_ = col
            board.ep_square = chess.square(file_, rank)
        else:
            board.ep_square = None

        return board.fen()
    return (tensor_to_fen,)


@app.cell
def __(mo):
    mo.md(
        r"""
        ## CSV loading, dedup, and deterministic train/val split

        - Reads `DATA_CSV_PATH` once.
        - Drops duplicate `Position` rows (the raw CSV has ~341k rows from
          repeated positions; deduping yields ~180k unique problem/best-move
          pairs as expected by the spec).
        - Derives the trace FEN per row by applying the UCI best move via
          `python-chess`. Rows where the move fails to apply are dropped.
        - Splits 95/5 by hashing each row's stable index with `SEED` so the
          split is identical across all stages and runs.
        """
    )
    return


@app.cell
def __(
    BEST_MOVE_COL,
    DATA_CSV_PATH,
    PROBLEM_FEN_COL,
    SEED,
    TRAIN_FRACTION,
    chess,
    hashlib,
    pd,
):
    def _hash_index_to_unit(idx: int, seed: int) -> float:
        """Deterministically hash (idx, seed) into a float in [0, 1)."""
        h = hashlib.blake2b(f"{seed}-{idx}".encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(h, "big") / 2**64

    def _derive_trace_fen(problem_fen, uci):
        """Apply `uci` to `problem_fen` and return the resulting FEN, or None.

        Robust to non-string inputs (pandas may parse missing cells as NaN).
        """
        if not isinstance(problem_fen, str) or not isinstance(uci, str):
            return None
        try:
            board = chess.Board(problem_fen)
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                return None
            board.push(move)
            return board.fen()
        except (ValueError, AssertionError):
            return None

    def load_pairs_dataframe(
        csv_path=DATA_CSV_PATH,
        problem_col: str = PROBLEM_FEN_COL,
        move_col: str = BEST_MOVE_COL,
        seed: int = SEED,
        train_fraction: float = TRAIN_FRACTION,
    ) -> pd.DataFrame:
        """Load the CSV, dedup, derive trace FENs, and assign a deterministic split.

        Returns a DataFrame with columns:
            problem_fen, best_move_uci, trace_fen, split
        where `split` is "train" or "val".
        """
        df = pd.read_csv(csv_path)
        if problem_col not in df.columns or move_col not in df.columns:
            raise KeyError(
                f"CSV missing required columns. Need {problem_col!r} and "
                f"{move_col!r}; have {list(df.columns)}."
            )

        # Keep only the columns we care about; drop dup positions.
        df = df[[problem_col, move_col]].rename(
            columns={problem_col: "problem_fen", move_col: "best_move_uci"}
        )
        df = df.drop_duplicates(subset=["problem_fen"]).reset_index(drop=True)

        # Derive trace FENs; drop rows where the move is invalid.
        df["trace_fen"] = [
            _derive_trace_fen(p, m)
            for p, m in zip(df["problem_fen"], df["best_move_uci"])
        ]
        df = df.dropna(subset=["trace_fen"]).reset_index(drop=True)

        # Deterministic split by hashing the row index.
        unit = [_hash_index_to_unit(i, seed) for i in range(len(df))]
        df["split"] = ["train" if u < train_fraction else "val" for u in unit]

        return df
    return (_derive_trace_fen, _hash_index_to_unit, load_pairs_dataframe)


@app.cell
def __(mo):
    mo.md(
        r"""
        ## Corruption strategies

        Each strategy returns an 8×8×18 float tensor representing a corrupted
        trace board. The three strategies are mixed per the spec's stage-
        dependent weights; the mix is supplied to `ChessPairDataset` as
        `(p_shuffle, p_legal, p_piece_swap)` summing to 1.

        - **batch_shuffle** is materialized at collate time, since it needs a
          sibling sample. `__getitem__` only marks it as the chosen kind and
          returns a placeholder.
        - **legal_move** picks a uniformly random legal move ≠ the best move and
          pushes it. Falls back to `batch_shuffle` if the only legal move is the
          best move.
        - **piece_swap** is one of two equally weighted operations on a copy of
          the clean trace tensor:
            1. Swap the contents of two occupied squares.
            2. Move one piece to a random square (overwriting whatever was
               there).
          Both produce a structurally non-reachable board.
        """
    )
    return


@app.cell
def __(BOARD_H, BOARD_W, PIECE_CHANNELS, chess, fen_to_tensor, torch):
    # Sentinel returned by ChessPairDataset when shuffle is the chosen kind, so
    # the collate fn knows to swap in a sibling. Using None inside a tuple
    # would break default_collate, so we use a distinct zero-shape tensor.
    SHUFFLE_SENTINEL = torch.zeros(0)

    def corrupt_legal_move(problem_fen: str, best_move_uci: str, rng):
        """Return (corrupted_trace_tensor, ok) where ok=False if no non-best
        legal move exists (caller should fall back to shuffle).
        """
        board = chess.Board(problem_fen)
        try:
            best_move = chess.Move.from_uci(best_move_uci)
        except ValueError:
            best_move = None

        legal = [m for m in board.legal_moves if m != best_move]
        if not legal:
            return None, False

        move = legal[rng.randrange(len(legal))]
        board.push(move)
        return fen_to_tensor(board.fen()), True

    def corrupt_piece_swap(clean_trace_tensor: torch.Tensor, rng):
        """Either swap two occupied squares' piece columns, or relocate one
        piece to a random square. Operates only on the 12 piece channels;
        metadata (12–17) is left untouched.
        """
        t = clean_trace_tensor.clone()
        pieces = t[:PIECE_CHANNELS]  # view: (12, 8, 8)

        # Find occupied squares (any piece channel hot).
        occupied = (pieces.sum(dim=0) > 0.5).nonzero(as_tuple=False)  # (N, 2): (row, col)
        if len(occupied) == 0:
            # Empty board — no-op corruption.
            return t

        if rng.random() < 0.5 and len(occupied) >= 2:
            # Swap two occupied squares.
            i, j = rng.sample(range(len(occupied)), 2)
            r1, c1 = int(occupied[i, 0]), int(occupied[i, 1])
            r2, c2 = int(occupied[j, 0]), int(occupied[j, 1])
            tmp = pieces[:, r1, c1].clone()
            pieces[:, r1, c1] = pieces[:, r2, c2]
            pieces[:, r2, c2] = tmp
        else:
            # Move one occupied piece to a random square (may overwrite).
            i = rng.randrange(len(occupied))
            r1, c1 = int(occupied[i, 0]), int(occupied[i, 1])
            r2 = rng.randrange(BOARD_H)
            c2 = rng.randrange(BOARD_W)
            piece_col = pieces[:, r1, c1].clone()
            pieces[:, r1, c1] = 0.0
            pieces[:, r2, c2] = piece_col

        return t
    return SHUFFLE_SENTINEL, corrupt_legal_move, corrupt_piece_swap


@app.cell
def __(mo):
    mo.md(
        r"""
        ## `BoardDataset` — single boards (stage 0)

        Yields a single 8×8×18 problem tensor per index. Used by the VQ-VAE
        pretraining stage, which is a pure reconstruction task and needs no
        trace pairs.
        """
    )
    return


@app.cell
def __(Dataset, fen_to_tensor, load_pairs_dataframe):
    class BoardDataset(Dataset):
        """Single-board dataset yielding 8×8×18 tensors of problem boards.

        Used by `training/stage0_vqvae.py`. Reuses the same CSV and split logic
        as ChessPairDataset so the train/val partitions are identical.
        """

        def __init__(self, split: str = "train", df=None):
            if split not in ("train", "val"):
                raise ValueError(f"split must be 'train' or 'val', got {split!r}")
            if df is None:
                df = load_pairs_dataframe()
            sub = df[df["split"] == split].reset_index(drop=True)
            self.problem_fens = sub["problem_fen"].tolist()

        def __len__(self) -> int:
            return len(self.problem_fens)

        def __getitem__(self, idx: int):
            return fen_to_tensor(self.problem_fens[idx])
    return (BoardDataset,)


@app.cell
def __(mo):
    mo.md(
        r"""
        ## `ChessPairDataset` — 3-tuples (stages 1–4)

        Per `__getitem__` returns:

        ```
        (problem_tensor, clean_trace_tensor, corrupted_trace_tensor)
        ```

        where every entry is `(18, 8, 8)` float32. The third slot is always
        materialized so the training-loop signature is uniform across stages:

        - `emit_corruption=True` (stages 1, 3, 4): the corrupted trace is
          generated according to the configured mix.
        - `emit_corruption=False` (stage 2): the corrupted trace is a zero
          tensor of the same shape, so the diffusion-only loop can ignore it
          without changing its unpacking.

        Random sampling uses a per-worker RNG seeded from `(SEED, worker_id,
        epoch)` to keep stage-internal runs reproducible while still varying
        between epochs.
        """
    )
    return


@app.cell
def __(
    BOARD_C,
    BOARD_H,
    BOARD_W,
    Dataset,
    SEED,
    SHUFFLE_SENTINEL,
    corrupt_legal_move,
    corrupt_piece_swap,
    fen_to_tensor,
    load_pairs_dataframe,
    random,
    torch,
):
    # Easy mix: stages 1–3. Hard mix: stage 4. Per spec.
    EASY_MIX = (0.30, 0.40, 0.30)
    HARD_MIX = (0.20, 0.60, 0.20)

    # Kind tags for the corruption strategies. Used internally; surfaced via
    # debug only.
    KIND_SHUFFLE = 0
    KIND_LEGAL = 1
    KIND_SWAP = 2

    class ChessPairDataset(Dataset):
        """3-tuple dataset for stages 1–4.

        Args:
            split: 'train' or 'val'.
            corruption_mix: (p_shuffle, p_legal, p_piece_swap), must sum to 1.
            emit_corruption: if False, the corrupted slot is filled with zeros
                regardless of the mix (used by stage 2 diffusion-only training,
                so the loop signature stays uniform).
            df: optional pre-loaded DataFrame from `load_pairs_dataframe`. If
                omitted, the dataframe is loaded once on construction.
            seed: base RNG seed for sample-level randomness.
        """

        def __init__(
            self,
            split: str = "train",
            corruption_mix=EASY_MIX,
            emit_corruption: bool = True,
            df=None,
            seed: int = SEED,
        ):
            if split not in ("train", "val"):
                raise ValueError(f"split must be 'train' or 'val', got {split!r}")
            if abs(sum(corruption_mix) - 1.0) > 1e-6:
                raise ValueError(
                    f"corruption_mix must sum to 1; got {corruption_mix} "
                    f"(sum={sum(corruption_mix)})"
                )
            if df is None:
                df = load_pairs_dataframe()
            sub = df[df["split"] == split].reset_index(drop=True)

            self.problem_fens = sub["problem_fen"].tolist()
            self.best_moves = sub["best_move_uci"].tolist()
            self.trace_fens = sub["trace_fen"].tolist()

            self.corruption_mix = tuple(corruption_mix)
            self.emit_corruption = emit_corruption
            self.seed = seed

        def __len__(self) -> int:
            return len(self.problem_fens)

        def _sample_kind(self, rng) -> int:
            r = rng.random()
            p_shuffle, p_legal, _ = self.corruption_mix
            if r < p_shuffle:
                return KIND_SHUFFLE
            if r < p_shuffle + p_legal:
                return KIND_LEGAL
            return KIND_SWAP

        def __getitem__(self, idx: int):
            problem_fen = self.problem_fens[idx]
            trace_fen = self.trace_fens[idx]

            problem_t = fen_to_tensor(problem_fen)
            clean_trace_t = fen_to_tensor(trace_fen)

            if not self.emit_corruption:
                # Stage 2 path: zero-fill so the unpacking is identical.
                corrupted_t = torch.zeros(BOARD_C, BOARD_H, BOARD_W, dtype=torch.float32)
                kind = -1
                return problem_t, clean_trace_t, corrupted_t, kind

            # Per-sample RNG: combine base seed with idx so individual sample
            # corruptions are reproducible across runs of the same epoch.
            rng = random.Random(self.seed * 1_000_003 + idx)
            kind = self._sample_kind(rng)

            if kind == KIND_SHUFFLE:
                # Defer to collate fn; mark with a sentinel.
                return problem_t, clean_trace_t, SHUFFLE_SENTINEL, kind

            if kind == KIND_LEGAL:
                corrupted_t, ok = corrupt_legal_move(
                    problem_fen, self.best_moves[idx], rng
                )
                if ok:
                    return problem_t, clean_trace_t, corrupted_t, KIND_LEGAL
                # Forced position fallback: defer to collate-time shuffle.
                return problem_t, clean_trace_t, SHUFFLE_SENTINEL, KIND_SHUFFLE

            # KIND_SWAP
            corrupted_t = corrupt_piece_swap(clean_trace_t, rng)
            return problem_t, clean_trace_t, corrupted_t, KIND_SWAP
    return (
        ChessPairDataset,
        EASY_MIX,
        HARD_MIX,
        KIND_LEGAL,
        KIND_SHUFFLE,
        KIND_SWAP,
    )


@app.cell
def __(mo):
    mo.md(
        r"""
        ## Collate function and `make_dataloader`

        The collate fn takes raw 4-tuples
        `(problem, clean_trace, corrupted_or_sentinel, kind)` and produces
        stacked batched tensors. For samples flagged as `KIND_SHUFFLE`, the
        corrupted trace is filled in by sampling a *different* index from the
        same batch. If the batch has only one sample, the shuffle target is
        the clean trace itself — a degenerate case that callers should avoid
        by using `batch_size >= 2`.

        Final batch shape: three tensors of shape `(B, 18, 8, 8)`. The kind
        vector is dropped after corruption resolution since downstream code
        does not need it.
        """
    )
    return


@app.cell
def __(
    BOARD_C,
    BOARD_H,
    BOARD_W,
    ChessPairDataset,
    DataLoader,
    EASY_MIX,
    KIND_SHUFFLE,
    SEED,
    torch,
):
    def chess_pair_collate(batch):
        """Resolve in-batch shuffle corruptions and stack into batched tensors.

        Input: list of 4-tuples `(problem, clean, corrupted_or_sentinel, kind)`.
        Output: 3-tuple of stacked tensors of shape `(B, 18, 8, 8)`.
        """
        B = len(batch)
        problems = torch.stack([row[0] for row in batch], dim=0)
        cleans = torch.stack([row[1] for row in batch], dim=0)
        corrupted_list = []

        # Pre-collect indices that need shuffle resolution.
        shuffle_indices = [i for i, row in enumerate(batch) if row[3] == KIND_SHUFFLE]
        # Pick replacement indices: for each shuffle slot, pick a different
        # row's clean trace. With B >= 2 we can always pick j != i.
        if B == 1 and shuffle_indices:
            # Degenerate: nothing to shuffle from. Use clean trace as a no-op.
            replacements = {i: batch[i][1] for i in shuffle_indices}
        else:
            replacements = {}
            for i in shuffle_indices:
                # Random pick that is not i. Using torch's RNG so it respects
                # the user's global seed setup.
                while True:
                    j = int(torch.randint(0, B, (1,)).item())
                    if j != i:
                        break
                replacements[i] = batch[j][1]

        for i, row in enumerate(batch):
            kind = row[3]
            if kind == KIND_SHUFFLE:
                corrupted_list.append(replacements[i])
            else:
                corrupted_list.append(row[2])
        corrupted = torch.stack(corrupted_list, dim=0)

        # Sanity: when emit_corruption is False, every kind is -1 and every
        # corrupted entry is already a zero tensor — no shuffle resolution
        # needed. The branches above naturally handle this.
        assert problems.shape == (B, BOARD_C, BOARD_H, BOARD_W)
        assert cleans.shape == (B, BOARD_C, BOARD_H, BOARD_W)
        assert corrupted.shape == (B, BOARD_C, BOARD_H, BOARD_W)
        return problems, cleans, corrupted

    def make_dataloader(
        split: str = "train",
        corruption_mix=EASY_MIX,
        emit_corruption: bool = True,
        batch_size: int = 64,
        num_workers: int = 4,
        shuffle=None,
        df=None,
        seed: int = SEED,
        pin_memory: bool = True,
        drop_last=None,
    ) -> DataLoader:
        """Construct the standard ChessPairDataset DataLoader.

        Defaults: shuffle=True for train, False for val; drop_last=True for
        train (avoids ragged final batches in the energy ranking loss),
        False for val.
        """
        if shuffle is None:
            shuffle = split == "train"
        if drop_last is None:
            drop_last = split == "train"

        ds = ChessPairDataset(
            split=split,
            corruption_mix=corruption_mix,
            emit_corruption=emit_corruption,
            df=df,
            seed=seed,
        )

        return DataLoader(
            ds,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            pin_memory=pin_memory,
            drop_last=drop_last,
            collate_fn=chess_pair_collate,
            persistent_workers=num_workers > 0,
        )
    return chess_pair_collate, make_dataloader


@app.cell
def __(mo):
    mo.md(
        r"""
        ## Sanity checks

        These cells exercise the helpers and datasets with tiny inputs. They
        execute on import (since marimo notebooks run dependency-ordered cells
        when imported as modules), so they MUST stay cheap and side-effect-
        free: no file writes, no training. Heavier visualization is rendered
        only when the notebook is opened with `marimo edit`.
        """
    )
    return


@app.cell
def __(BOARD_C, BOARD_H, BOARD_W, chess, fen_to_tensor, tensor_to_fen):
    # FEN round-trip on the starting position.
    _start = chess.STARTING_FEN
    _t = fen_to_tensor(_start)
    assert _t.shape == (BOARD_C, BOARD_H, BOARD_W), _t.shape
    assert _t.dtype.is_floating_point
    # 32 pieces in the starting position.
    assert int(_t[:12].sum().item()) == 32
    # White to move at start.
    assert float(_t[12].mean().item()) == 1.0
    # All four castling rights.
    for _c in (13, 14, 15, 16):
        assert float(_t[_c].mean().item()) == 1.0
    # No en passant.
    assert float(_t[17].sum().item()) == 0.0

    # Round-trip should produce a board equivalent to start (positions, side,
    # castling, ep equal). FEN clocks differ since we don't encode them.
    _back = tensor_to_fen(_t)
    _b1 = chess.Board(_start)
    _b2 = chess.Board(_back)
    assert _b1.board_fen() == _b2.board_fen()
    assert _b1.turn == _b2.turn
    assert _b1.castling_rights == _b2.castling_rights
    assert _b1.ep_square == _b2.ep_square

    print("FEN round-trip OK on starting position.")
    return


@app.cell
def __(chess, corrupt_legal_move, corrupt_piece_swap, fen_to_tensor, random):
    # Corruption strategies on the starting position.
    _start = chess.STARTING_FEN
    _rng = random.Random(0)

    _legal_t, _ok = corrupt_legal_move(_start, "e2e4", _rng)
    assert _ok, "starting position has many legal moves besides e2e4"
    assert _legal_t.shape == (18, 8, 8)

    _clean_t = fen_to_tensor(_start)
    _swapped_t = corrupt_piece_swap(_clean_t, _rng)
    assert _swapped_t.shape == _clean_t.shape
    # Swap should preserve total piece mass on the 12 piece channels (it
    # either swaps occupied squares or moves one piece, both mass-preserving
    # unless the destination was already occupied — in which case the count
    # may decrease, never increase).
    assert _swapped_t[:12].sum() <= _clean_t[:12].sum() + 1e-5

    print("Corruption strategies OK.")
    return


@app.cell
def __(
    BOARD_C,
    BOARD_H,
    BOARD_W,
    DataLoader,
    EASY_MIX,
    chess_pair_collate,
    load_pairs_dataframe,
    ChessPairDataset,
):
    # End-to-end: build a tiny dataset, pull one batch, check shapes.
    # This loads the CSV. It's cached/reused if any other cell already loaded
    # it during import; otherwise it incurs a one-time pandas read. Keep
    # batch and worker count small so import stays fast.
    _df = load_pairs_dataframe()
    print(
        f"Loaded {len(_df)} unique problem rows; "
        f"train={(_df['split'] == 'train').sum()} "
        f"val={(_df['split'] == 'val').sum()}"
    )

    _ds = ChessPairDataset(
        split="val",
        corruption_mix=EASY_MIX,
        emit_corruption=True,
        df=_df,
    )
    print(f"Val ChessPairDataset size: {len(_ds)}")

    _loader = DataLoader(
        _ds,
        batch_size=4,
        shuffle=False,
        num_workers=0,
        collate_fn=chess_pair_collate,
    )
    _problems, _cleans, _corrupted = next(iter(_loader))
    assert _problems.shape == (4, BOARD_C, BOARD_H, BOARD_W)
    assert _cleans.shape == (4, BOARD_C, BOARD_H, BOARD_W)
    assert _corrupted.shape == (4, BOARD_C, BOARD_H, BOARD_W)
    print("Batch shapes OK:", _problems.shape, _cleans.shape, _corrupted.shape)

    # Verify the emit_corruption=False path produces zeros.
    _ds_zeros = ChessPairDataset(
        split="val",
        corruption_mix=EASY_MIX,
        emit_corruption=False,
        df=_df,
    )
    _loader_zeros = DataLoader(
        _ds_zeros,
        batch_size=4,
        shuffle=False,
        num_workers=0,
        collate_fn=chess_pair_collate,
    )
    _, _, _corrupted_zeros = next(iter(_loader_zeros))
    assert (_corrupted_zeros == 0).all(), "emit_corruption=False should zero-fill"
    print("emit_corruption=False path zero-fills OK.")
    return


@app.cell
def __(BoardDataset, load_pairs_dataframe):
    # BoardDataset (stage 0) sanity: yields a single (18, 8, 8) tensor.
    _df = load_pairs_dataframe()
    _bd = BoardDataset(split="val", df=_df)
    _sample = _bd[0]
    assert _sample.shape == (18, 8, 8)
    print(f"BoardDataset OK; val size = {len(_bd)}, sample shape = {tuple(_sample.shape)}")
    return


if __name__ == "__main__":
    app.run()
