import marimo

__generated_with = "0.23.1"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import torch
    from torch import nn
    import torch.nn.functional as F
    from diffusers import VQModel
    from diffusers.optimization import get_cosine_schedule_with_warmup
    from accelerate import Accelerator
    from sklearn.model_selection import train_test_split
    from torch.utils.data import Dataset, DataLoader, random_split, Subset
    from torch.optim import AdamW
    import os
    import gc
    import json
    import random
    import sys
    import time
    from pathlib import Path
    import numpy as np
    import pandas as pd
    import chess
    import matplotlib.pyplot as plt
    from IPython.display import clear_output, display
    from tqdm.auto import tqdm

    # torch_ema is optional; fall back to a no-op if missing so the notebook
    # runs on fresh envs without that package.
    try:
        from torch_ema import ExponentialMovingAverage
    except ImportError:

        class ExponentialMovingAverage:
            def __init__(self, params, decay=0.99):
                self.params = list(params)
                self.decay = decay

            def update(self):
                pass

            def average_parameters(self):
                from contextlib import contextmanager

                @contextmanager
                def _noop():
                    yield

                return _noop()


    torch.backends.cudnn.benchmark = True
    torch.set_float32_matmul_precision("high")

    # Auto-detect the best available device: CUDA > MPS (Apple Silicon) > CPU.
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"Using device: {device}")
    return (
        Accelerator,
        DataLoader,
        Dataset,
        ExponentialMovingAverage,
        F,
        Path,
        Subset,
        VQModel,
        chess,
        device,
        get_cosine_schedule_with_warmup,
        json,
        np,
        os,
        pd,
        plt,
        sys,
        time,
        torch,
        tqdm,
        train_test_split,
    )


@app.cell
def _():
    class TrainingConfig:
        # Board is 8x8, so "sample_size" is literally 8
        board_size = 8

        # Channel count from LichessEvalDataset when all flags are on:
        # 12 piece planes + 1 turn + 4 castling + 1 ep + 1 halfmove + 1 fullmove = 20
        num_channels = 20

        # Small defaults so the notebook runs on a laptop-sized sample.
        # Bump these up when you point at the full Lichess dump.
        train_batch_size = 8
        gradient_accumulation_steps = 1
        eval_batch_size = 8
        num_epochs = 100

        learning_rate = 1e-4
        lr_warmup_steps = 100

        # Mixed precision is only used when CUDA is present; see train_loop.
        mixed_precision = "no"  # flip to "bf16" once you're on CUDA
        output_dir = "/workspace/vqvae"
        seed = 42
        validation_epoch = 1
        validation_split = 0.2  # big-ish split because the sample file is tiny

        # Loss weighting. Piece planes are one-hot and semantically dominant;
        # scalar planes (turn, castling, ep, clocks) get their own term so MSE
        # on them doesn't get drowned out.
        reconstruction_weight: float = 1.0
        commitment_weight: float = 1.0
        piece_ce_weight: float = 1.0  # 13-class cross-entropy (empty + 12 pieces)
        scalar_mse_weight: float = 0.5  # MSE on the non-piece planes
        piece_mse_weight: float = (
            0.25  # MSE on piece planes (helps stabilize early)
        )

        # Path to your JSONL file (lichess_db_eval format).
        jsonl_path = "/workspace/lichess_evals_sample.jsonl"

        # DataLoader workers. Keep at 0 on tiny datasets to avoid multi-process
        # startup overhead; push to 8-16 on the real DB.
        num_workers = 0


    config = TrainingConfig()
    return (config,)


@app.cell
def _(chess, np, plt, torch):
    # ------------------------------------------------------------------
    # Board rendering / visualization helpers (replaces PIL grayscale utils)
    # ------------------------------------------------------------------

    PIECE_SYMBOLS = {
        0: "\u2659",
        1: "\u2658",
        2: "\u2657",
        3: "\u2656",
        4: "\u2655",
        5: "\u2654",
        6: "\u265f",
        7: "\u265e",
        8: "\u265d",
        9: "\u265c",
        10: "\u265b",
        11: "\u265a",
    }


    def tensor_to_fen(x):
        """
        Invert LichessEvalDataset.fen_to_tensor well enough to get a legal-ish FEN
        back for display. Accepts (C, 8, 8) or (8, 8, C). Clocks default.
        """
        if isinstance(x, torch.Tensor):
            x = x.detach().cpu().numpy()
        if x.shape[0] != 8:
            x = np.transpose(x, (1, 2, 0))
        C = x.shape[-1]

        board = chess.Board.empty()
        piece_symbols_by_ch = "PNBRQKpnbrqk"
        piece_logits = x[..., :12]
        best_ch = piece_logits.argmax(axis=-1)
        best_val = piece_logits.max(axis=-1)
        for row in range(8):
            for col in range(8):
                if best_val[row, col] > 0.5:
                    square = chess.square(col, 7 - row)
                    piece = chess.Piece.from_symbol(
                        piece_symbols_by_ch[best_ch[row, col]]
                    )
                    board.set_piece_at(square, piece)

        if C > 12:
            board.turn = chess.WHITE if x[..., 12].mean() > 0.5 else chess.BLACK

        castling_fen = ""
        if C > 16:
            if x[..., 13].mean() > 0.5:
                castling_fen += "K"
            if x[..., 14].mean() > 0.5:
                castling_fen += "Q"
            if x[..., 15].mean() > 0.5:
                castling_fen += "k"
            if x[..., 16].mean() > 0.5:
                castling_fen += "q"

        try:
            fen = board.board_fen()
            side = "w" if board.turn == chess.WHITE else "b"
            castling = castling_fen if castling_fen else "-"
            return f"{fen} {side} {castling} - 0 1"
        except Exception:
            return board.board_fen()


    def render_board_ascii(x):
        """Return a unicode ASCII chess board string from a (C,8,8) or (8,8,C) tensor."""
        if isinstance(x, torch.Tensor):
            x = x.detach().cpu().numpy()
        if x.shape[0] != 8:
            x = np.transpose(x, (1, 2, 0))
        piece_logits = x[..., :12]
        best_ch = piece_logits.argmax(axis=-1)
        best_val = piece_logits.max(axis=-1)
        rows = []
        for row in range(8):
            cells = []
            for col in range(8):
                if best_val[row, col] > 0.5:
                    cells.append(PIECE_SYMBOLS[int(best_ch[row, col])])
                else:
                    cells.append("\u00b7")
            rows.append(" ".join(cells))
        return "\n".join(rows)


    def display_board_tensors(tensors, titles=None, figsize=(12, 4)):
        """Plot one or more board tensors side-by-side as occupancy heatmaps."""
        if isinstance(tensors, torch.Tensor):
            tensors = [tensors]
        n = len(tensors)
        fig, axes = plt.subplots(1, n, figsize=figsize)
        if n == 1:
            axes = [axes]
        for i, (ax, x) in enumerate(zip(axes, tensors)):
            if isinstance(x, torch.Tensor):
                x = x.detach().cpu().numpy()
            if x.shape[0] != 8:
                x = np.transpose(x, (1, 2, 0))
            occupancy = x[..., :12].max(axis=-1)
            ax.imshow(occupancy, cmap="viridis", vmin=0.0, vmax=1.0)
            ax.set_xticks(range(8))
            ax.set_yticks(range(8))
            ax.set_xticklabels(list("abcdefgh"))
            ax.set_yticklabels(list("87654321"))
            piece_logits = x[..., :12]
            best_ch = piece_logits.argmax(axis=-1)
            best_val = piece_logits.max(axis=-1)
            for r in range(8):
                for c in range(8):
                    if best_val[r, c] > 0.5:
                        ax.text(
                            c,
                            r,
                            PIECE_SYMBOLS[int(best_ch[r, c])],
                            ha="center",
                            va="center",
                            fontsize=20,
                            color="white",
                        )
            if titles and i < len(titles):
                ax.set_title(titles[i])
        plt.tight_layout()
        plt.show()

    return (display_board_tensors,)


@app.cell
def _(Dataset, chess, np, pd, torch):
    # ------------------------------------------------------------------
    # LichessEvalDataset --- mirrors chess_dataset.marimo.py so this notebook
    # is self-contained. If you prefer, replace this cell with:
    #     from chess_dataset import LichessEvalDataset
    # ------------------------------------------------------------------

    PIECE_TO_CHANNEL = {
        "P": 0,
        "N": 1,
        "B": 2,
        "R": 3,
        "Q": 4,
        "K": 5,
        "p": 6,
        "n": 7,
        "b": 8,
        "r": 9,
        "q": 10,
        "k": 11,
    }


    class LichessEvalDataset(Dataset):
        """
        Returns (x, y) where
            x : (8, 8, C) float tensor of board planes
            y : scalar float tensor, Stockfish eval target
        """

        def __init__(
            self,
            data,
            include_turn=True,
            include_castling=True,
            include_ep=True,
            include_halfmove=True,
            include_fullmove=True,
            mate_value=10000.0,
            drop_mate=False,
            target_mode="energy",
            clip_eval=1000.0,
            normalize_eval=True,
            dtype=torch.float32,
            validate_fen=True,
            score_pov="side_to_move",
        ):
            if isinstance(data, str):
                if data.endswith(".csv"):
                    self.df = pd.read_csv(data)
                elif data.endswith(".parquet"):
                    self.df = pd.read_parquet(data)
                else:
                    raise ValueError("Supported file types: .csv, .parquet")
            else:
                self.df = data.copy()

            required = {"fen", "cp", "mate"}
            missing = required - set(self.df.columns)
            if missing:
                raise ValueError(f"Missing required columns: {missing}")

            self.include_turn = include_turn
            self.include_castling = include_castling
            self.include_ep = include_ep
            self.include_halfmove = include_halfmove
            self.include_fullmove = include_fullmove
            self.mate_value = float(mate_value)
            self.drop_mate = drop_mate
            self.target_mode = target_mode
            self.clip_eval = float(clip_eval)
            self.normalize_eval = normalize_eval
            self.dtype = dtype
            self.validate_fen = validate_fen
            self.score_pov = score_pov

            self.df = self.df.reset_index(drop=True)
            if self.drop_mate:
                self.df = self.df[self.df["cp"].notna()].reset_index(drop=True)
            if self.validate_fen:
                self._validate_fens()
            self.df = self.df[
                self.df["cp"].notna() | self.df["mate"].notna()
            ].reset_index(drop=True)
            if len(self.df) == 0:
                raise ValueError("No valid rows left after filtering")

            self.channel_names = self._build_channel_names()

        def _build_channel_names(self):
            names = [
                "white_pawn",
                "white_knight",
                "white_bishop",
                "white_rook",
                "white_queen",
                "white_king",
                "black_pawn",
                "black_knight",
                "black_bishop",
                "black_rook",
                "black_queen",
                "black_king",
            ]
            if self.include_turn:
                names.append("turn")
            if self.include_castling:
                names.extend(
                    [
                        "white_kingside_castle",
                        "white_queenside_castle",
                        "black_kingside_castle",
                        "black_queenside_castle",
                    ]
                )
            if self.include_ep:
                names.append("en_passant")
            if self.include_halfmove:
                names.append("halfmove_clock")
            if self.include_fullmove:
                names.append("fullmove_number")
            return names

        def _validate_fens(self):
            valid_rows = []
            for fen in self.df["fen"]:
                try:
                    chess.Board(fen)
                    valid_rows.append(True)
                except Exception:
                    valid_rows.append(False)
            self.df = self.df[np.array(valid_rows)].reset_index(drop=True)

        def __len__(self):
            return len(self.df)

        def fen_to_tensor(self, fen: str):
            board = chess.Board(fen)
            num_channels = len(self.channel_names)
            x = np.zeros((8, 8, num_channels), dtype=np.float32)

            for square, piece in board.piece_map().items():
                row = 7 - chess.square_rank(square)
                col = chess.square_file(square)
                ch = PIECE_TO_CHANNEL[piece.symbol()]
                x[row, col, ch] = 1.0

            ch_idx = 12
            if self.include_turn:
                x[:, :, ch_idx] = 1.0 if board.turn == chess.WHITE else 0.0
                ch_idx += 1
            if self.include_castling:
                if board.has_kingside_castling_rights(chess.WHITE):
                    x[:, :, ch_idx] = 1.0
                ch_idx += 1
                if board.has_queenside_castling_rights(chess.WHITE):
                    x[:, :, ch_idx] = 1.0
                ch_idx += 1
                if board.has_kingside_castling_rights(chess.BLACK):
                    x[:, :, ch_idx] = 1.0
                ch_idx += 1
                if board.has_queenside_castling_rights(chess.BLACK):
                    x[:, :, ch_idx] = 1.0
                ch_idx += 1
            if self.include_ep:
                if board.ep_square is not None:
                    row = 7 - chess.square_rank(board.ep_square)
                    col = chess.square_file(board.ep_square)
                    x[row, col, ch_idx] = 1.0
                ch_idx += 1
            if self.include_halfmove:
                x[:, :, ch_idx] = float(board.halfmove_clock) / 100.0
                ch_idx += 1
            if self.include_fullmove:
                x[:, :, ch_idx] = min(float(board.fullmove_number) / 200.0, 1.0)
                ch_idx += 1

            return x

        def _raw_eval_from_row(self, row):
            cp = row["cp"]
            mate = row["mate"]
            if pd.notna(cp):
                return float(cp)
            if pd.notna(mate):
                mate = float(mate)
                if self.drop_mate:
                    raise ValueError("Mate row found while drop_mate=True")
                return self.mate_value if mate > 0 else -self.mate_value
            raise ValueError("Row has neither cp nor mate")

        def apply_score_pov(self, y, fen):
            board = chess.Board(fen)
            if self.score_pov == "white":
                return y
            elif self.score_pov == "black":
                return -y
            elif self.score_pov == "side_to_move":
                return y if board.turn == chess.WHITE else -y
            else:
                raise ValueError(
                    "score_pov must be 'white', 'black', or 'side_to_move'"
                )

        def target_from_row(self, row):
            if self.target_mode == "cp_only":
                if pd.isna(row["cp"]):
                    raise ValueError("cp_only mode encountered mate-only row")
                y = float(row["cp"])
            elif self.target_mode == "cp_or_mate":
                y = self._raw_eval_from_row(row)
            elif self.target_mode == "energy":
                y = self._raw_eval_from_row(row)
                y = np.clip(y, -self.clip_eval, self.clip_eval)
                if self.normalize_eval:
                    y = y / self.clip_eval
            else:
                raise ValueError(
                    "target_mode must be one of: ['cp_only', 'cp_or_mate', 'energy']"
                )
            y = self.apply_score_pov(y, row["fen"])
            return float(y)

        def __getitem__(self, idx):
            row = self.df.iloc[idx]
            x = self.fen_to_tensor(row["fen"])
            y = self.target_from_row(row)
            return (
                torch.tensor(x, dtype=self.dtype),
                torch.tensor(y, dtype=self.dtype),
            )


    def extract_fen_cp_mate_from_record(rec):
        fen = rec["fen"]
        evals = rec.get("evals", [])
        if not evals:
            return fen, np.nan, np.nan
        best_eval = max(evals, key=lambda e: e.get("depth", -1))
        pvs = best_eval.get("pvs", [])
        if not pvs:
            return fen, np.nan, np.nan
        best_pv = pvs[0]
        cp = best_pv.get("cp", None)
        mate = best_pv.get("mate", None)
        cp = float(cp) if cp is not None else np.nan
        mate = float(mate) if mate is not None else np.nan
        return fen, cp, mate


    def records_to_fen_cp_mate_df(records):
        rows = []
        for rec in records:
            fen, cp, mate = extract_fen_cp_mate_from_record(rec)
            rows.append({"fen": fen, "cp": cp, "mate": mate})
        return pd.DataFrame(rows)

    return LichessEvalDataset, records_to_fen_cp_mate_df


@app.cell
def _(
    DataLoader,
    LichessEvalDataset,
    Subset,
    config,
    display_board_tensors,
    json,
    records_to_fen_cp_mate_df,
    train_test_split,
):
    # ------------------------------------------------------------------
    # Build dataset, splits, and dataloaders from the lichess JSONL.
    # Wrapped in a function so locals (records, df, xb, yb, indices, ...)
    # don't leak into the marimo dataflow graph. Only the things we actually
    # need later are returned.
    # ------------------------------------------------------------------


    def _build_dataloaders():
        records = []
        with open(config.jsonl_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))

        df = records_to_fen_cp_mate_df(records)
        print(f"Loaded {len(df)} positions from {config.jsonl_path}")

        full_ds = LichessEvalDataset(
            data=df,
            include_turn=True,
            include_castling=True,
            include_ep=True,
            include_halfmove=True,
            include_fullmove=True,
            mate_value=10000.0,
            drop_mate=False,
            target_mode="energy",
            clip_eval=1000.0,
            normalize_eval=True,
            score_pov="side_to_move",
        )

        C_actual = len(full_ds.channel_names)
        assert C_actual == config.num_channels, (
            f"Channel mismatch: dataset has {C_actual}, config expects {config.num_channels}"
        )
        print(f"Board channels: {C_actual} -> {full_ds.channel_names}")

        train_idx, val_idx = train_test_split(
            range(len(full_ds)),
            test_size=config.validation_split,
            random_state=config.seed,
        )
        train_ds = Subset(full_ds, train_idx)
        val_ds = Subset(full_ds, val_idx)

        train_dl = DataLoader(
            train_ds,
            batch_size=config.train_batch_size,
            shuffle=True,
            num_workers=config.num_workers,
            drop_last=False,
        )
        val_dl = DataLoader(
            val_ds,
            batch_size=config.eval_batch_size,
            shuffle=False,
            num_workers=config.num_workers,
        )
        print(
            f"Train: {len(train_idx)} samples ({len(train_dl)} batches) | "
            f"Val: {len(val_idx)} samples ({len(val_dl)} batches)"
        )

        # Peek at one batch for sanity. Dataset yields (B, 8, 8, C); we permute
        # to (B, C, 8, 8) for conv2d.
        peek_xb, peek_yb = next(iter(train_dl))
        peek_chw = peek_xb.permute(0, 3, 1, 2).contiguous()
        print(f"Raw batch x: {tuple(peek_xb.shape)}  (B, H, W, C)")
        print(f"Conv-ready x: {tuple(peek_chw.shape)}  (B, C, H, W)")
        print(
            f"Target y shape: {tuple(peek_yb.shape)}, values: {peek_yb.tolist()}"
        )

        n_show = min(2, peek_chw.shape[0])
        display_board_tensors(
            [peek_chw[i] for i in range(n_show)],
            titles=[
                f"board {i}  y={peek_yb[i].item():.3f}" for i in range(n_show)
            ],
        )

        return train_dl, val_dl, full_ds


    train_dataloader, val_dataloader, full_dataset = _build_dataloaders()
    return train_dataloader, val_dataloader


@app.cell
def _(
    VQModel,
    config,
    device,
    get_cosine_schedule_with_warmup,
    torch,
    train_dataloader,
):
    # ------------------------------------------------------------------
    # VQ-VAE model for 8x8 chess boards.
    #
    # Input/output: (B, 20, 8, 8) --- the 20 board planes.
    # Two down/up blocks give one 2x downsample: 8x8 -> 4x4 latent grid.
    # Codebook: 1024 entries. norm_num_groups=8 because the base width is 64.
    # No xformers (pointless at this resolution, and CUDA-only anyway).
    # ------------------------------------------------------------------

    model = VQModel(
        sample_size=config.board_size,
        in_channels=config.num_channels,
        out_channels=config.num_channels,
        down_block_types=("DownEncoderBlock2D", "DownEncoderBlock2D"),
        up_block_types=("UpDecoderBlock2D", "UpDecoderBlock2D"),
        block_out_channels=(64, 128),
        layers_per_block=2,
        mid_block_add_attention=True,
        latent_channels=4,
        num_vq_embeddings=1024,
        scaling_factor=1.0,
        act_fn="silu",
        norm_type="group",
        norm_num_groups=8,
        force_upcast=False,
        lookup_from_codebook=True,
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        betas=(0.9, 0.999),
        weight_decay=0.01,
        eps=1e-8,
    )

    lr_scheduler = get_cosine_schedule_with_warmup(
        optimizer=optimizer,
        num_warmup_steps=config.lr_warmup_steps,
        num_training_steps=(len(train_dataloader) * config.num_epochs),
    )

    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model params: {n_params:,}  (device={device})")
    return lr_scheduler, model, optimizer


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Alternative "no-downsample" config --- keeps the latent at full 8x8 resolution,
    preserving per-square semantics at the cost of a larger latent grid:

    ```python
    model = VQModel(
        sample_size=8,
        in_channels=20, out_channels=20,
        down_block_types=("DownEncoderBlock2D",),
        up_block_types=("UpDecoderBlock2D",),
        block_out_channels=(128,),
        layers_per_block=2,
        mid_block_add_attention=True,
        latent_channels=4,
        num_vq_embeddings=1024,
        norm_type="group", norm_num_groups=8,
        force_upcast=False, lookup_from_codebook=True,
    ).to(device)
    ```
    """)
    return


@app.cell
def _(F, config, torch):
    # ------------------------------------------------------------------
    # Loss helpers. Two kinds of planes get scored differently:
    #   - Piece planes (ch 0..11) are one-hot: 13-class CE + small MSE stabilizer.
    #   - Scalar/flag planes (ch 12..19) are plain MSE.
    # ------------------------------------------------------------------

    PIECE_CHANNELS = 12


    def split_planes(x):
        """(B, C, 8, 8) -> (piece_planes, scalar_planes)"""
        return x[:, :PIECE_CHANNELS], x[:, PIECE_CHANNELS:]


    def piece_targets_from_onehot(piece_planes):
        """
        piece_planes: (B, 12, 8, 8) one-hot. Returns class index (B, 8, 8)
        where 0 = empty, 1..12 = piece channel + 1.
        """
        occupied = piece_planes.sum(dim=1) > 0.5
        piece_idx = piece_planes.argmax(dim=1) + 1
        return torch.where(occupied, piece_idx, torch.zeros_like(piece_idx))


    def piece_class_logits(pred_piece_planes):
        """Prepend an 'empty' channel so softmax competes empty vs best piece."""
        empty_logit = -pred_piece_planes.amax(dim=1, keepdim=True)
        return torch.cat([empty_logit, pred_piece_planes], dim=1)


    def chess_reconstruction_loss(pred, target):
        """pred, target: (B, 20, 8, 8). Returns (total_recon, breakdown)."""
        pred_pieces, pred_scalars = split_planes(pred)
        tgt_pieces, tgt_scalars = split_planes(target)

        logits = piece_class_logits(pred_pieces)
        classes = piece_targets_from_onehot(tgt_pieces)
        piece_ce = F.cross_entropy(logits, classes)

        piece_mse = F.mse_loss(pred_pieces, tgt_pieces)
        if pred_scalars.shape[1] > 0:
            scalar_mse = F.mse_loss(pred_scalars, tgt_scalars)
        else:
            scalar_mse = torch.tensor(0.0, device=pred.device)

        recon = (
            config.piece_ce_weight * piece_ce
            + config.piece_mse_weight * piece_mse
            + config.scalar_mse_weight * scalar_mse
        )
        return recon, {
            "piece_ce": piece_ce.detach(),
            "piece_mse": piece_mse.detach(),
            "scalar_mse": scalar_mse.detach(),
        }


    def piece_accuracy(pred, target):
        """Per-square piece-class accuracy (including 'empty'). Python float."""
        pred_pieces, _ = split_planes(pred)
        tgt_pieces, _ = split_planes(target)
        logits = piece_class_logits(pred_pieces)
        pred_classes = logits.argmax(dim=1)
        tgt_classes = piece_targets_from_onehot(tgt_pieces)
        return (pred_classes == tgt_classes).float().mean().item()

    return chess_reconstruction_loss, piece_accuracy


@app.cell
def _(torch):
    def sample_boards(model, val_dataloader, samples=2):
        """Grab a small batch, return (orig, recon) tensor pairs + titles for plotting."""
        model.eval()
        with torch.no_grad():
            xb, _yb = next(iter(val_dataloader))
            xb = (
                xb[:samples]
                .permute(0, 3, 1, 2)
                .contiguous()
                .to(next(model.parameters()).device)
            )
            out = model(xb).sample
        pairs, titles = [], []
        for i in range(xb.shape[0]):
            pairs.append(xb[i])
            pairs.append(out[i])
            titles.append(f"orig {i}")
            titles.append(f"recon {i}")
        return pairs, titles

    return (sample_boards,)


@app.cell
def _(
    Accelerator,
    ExponentialMovingAverage,
    chess_reconstruction_loss,
    display_board_tensors,
    np,
    os,
    piece_accuracy,
    sample_boards,
    sys,
    time,
    torch,
):
    def train_loop(
        config, model, optimizer, train_dataloader, val_dataloader, lr_scheduler
    ):
        if torch.cuda.is_available():
            torch.backends.cuda.matmul.allow_tf32 = True
        torch.set_float32_matmul_precision("high")

        # Only use mixed precision when CUDA is actually available.
        mp = config.mixed_precision if torch.cuda.is_available() else "no"
        accelerator = Accelerator(
            mixed_precision=mp,
            gradient_accumulation_steps=config.gradient_accumulation_steps,
        )
        model, optimizer, train_dataloader, val_dataloader, lr_scheduler = (
            accelerator.prepare(
                model, optimizer, train_dataloader, val_dataloader, lr_scheduler
            )
        )
        ema = ExponentialMovingAverage(model.parameters(), decay=0.99)

        os.makedirs(config.output_dir, exist_ok=True)

        global_step = 0
        loss_logging = []

        for epoch in range(config.num_epochs):
            model.train()
            t_loss = t_recon = t_commit = t_ce = t_pmse = t_smse = t_acc = 0.0
            epoch_start = time.time()

            for step, batch in enumerate(train_dataloader):
                with accelerator.accumulate(model):
                    xb, _yb = batch  # (B, 8, 8, C), (B,)
                    images = xb.permute(0, 3, 1, 2).contiguous()  # (B, C, 8, 8)

                    model_output = model(images)
                    recon_loss, parts = chess_reconstruction_loss(
                        model_output.sample, images
                    )
                    commit_loss = model_output.commit_loss.mean()
                    total_loss = (
                        config.reconstruction_weight * recon_loss
                        + config.commitment_weight * commit_loss
                    )

                    accelerator.backward(total_loss)
                    if accelerator.sync_gradients:
                        accelerator.clip_grad_norm_(model.parameters(), 1.0)
                        optimizer.step()
                        lr_scheduler.step()
                        optimizer.zero_grad()
                    ema.update()

                    t_loss += total_loss.item()
                    t_recon += recon_loss.item()
                    t_commit += commit_loss.item()
                    t_ce += parts["piece_ce"].item()
                    t_pmse += parts["piece_mse"].item()
                    t_smse += parts["scalar_mse"].item()
                    t_acc += piece_accuracy(model_output.sample, images)

                    elapsed = time.time() - epoch_start
                    steps_remaining = len(train_dataloader) - (step + 1)
                    avg_time_per_step = elapsed / (step + 1)
                    eta = avg_time_per_step * steps_remaining
                    m_, s_ = divmod(int(eta), 60)
                    h_, m_ = divmod(m_, 60)
                    eta_str = f"{h_:02d}:{m_:02d}:{s_:02d}"
                    sys.stdout.write(
                        f"Epoch {epoch + 1}/{config.num_epochs} | "
                        f"Step {step + 1}/{len(train_dataloader)} | ETA: {eta_str} | "
                        f"loss: {t_loss / (step + 1):.4f} | "
                        f"recon: {t_recon / (step + 1):.4f} | "
                        f"ce: {t_ce / (step + 1):.4f} | "
                        f"p_mse: {t_pmse / (step + 1):.4f} | "
                        f"s_mse: {t_smse / (step + 1):.4f} | "
                        f"commit: {t_commit / (step + 1):.4f} | "
                        f"piece_acc: {t_acc / (step + 1):.4f} | "
                        f"lr: {lr_scheduler.get_last_lr()[0]:.2e}   \r"
                    )
                    sys.stdout.flush()
                    global_step += 1
            print()

            if (epoch + 1) % config.validation_epoch == 0:
                model.eval()
                val_start = time.time()
                v_loss = v_recon = v_commit = v_ce = v_pmse = v_smse = v_acc = 0.0

                with torch.no_grad():
                    with ema.average_parameters():
                        for vstep, vbatch in enumerate(val_dataloader):
                            xb, _yb = vbatch
                            images = xb.permute(0, 3, 1, 2).contiguous()

                            model_output = model(images)
                            recon_loss, parts = chess_reconstruction_loss(
                                model_output.sample, images
                            )
                            commit_loss = model_output.commit_loss.mean()
                            total = (
                                config.reconstruction_weight * recon_loss
                                + config.commitment_weight * commit_loss
                            )

                            v_loss += total.item()
                            v_recon += recon_loss.item()
                            v_commit += commit_loss.item()
                            v_ce += parts["piece_ce"].item()
                            v_pmse += parts["piece_mse"].item()
                            v_smse += parts["scalar_mse"].item()
                            v_acc += piece_accuracy(model_output.sample, images)

                            elapsed = time.time() - val_start
                            steps_remaining = len(val_dataloader) - (vstep + 1)
                            avg_time_per_step = elapsed / (vstep + 1)
                            eta = avg_time_per_step * steps_remaining
                            m_, s_ = divmod(int(eta), 60)
                            h_, m_ = divmod(m_, 60)
                            eta_str = f"{h_:02d}:{m_:02d}:{s_:02d}"
                            sys.stdout.write(
                                f"Validation | Step {vstep + 1}/{len(val_dataloader)} | "
                                f"ETA: {eta_str} | "
                                f"loss: {v_loss / (vstep + 1):.4f} | "
                                f"ce: {v_ce / (vstep + 1):.4f} | "
                                f"piece_acc: {v_acc / (vstep + 1):.4f}   \r"
                            )
                            sys.stdout.flush()

                nval = max(len(val_dataloader), 1)
                avg_val_loss = v_loss / nval
                avg_val_ce = v_ce / nval
                avg_val_acc = v_acc / nval
                print(
                    f"\nValidation: loss={avg_val_loss:.4f}, ce={avg_val_ce:.4f}, "
                    f"piece_acc={avg_val_acc:.4f}"
                )
                loss_logging.append(
                    (t_loss / len(train_dataloader), avg_val_loss, avg_val_acc)
                )

                if accelerator.is_main_process:
                    pairs, titles = sample_boards(model, val_dataloader, samples=2)
                    print("Samples (orig / recon):")
                    display_board_tensors(
                        pairs, titles=titles, figsize=(4 * len(pairs), 4)
                    )

                    with ema.average_parameters():
                        unwrapped_model = accelerator.unwrap_model(model)
                        unwrapped_model.save_pretrained(config.output_dir)
                        print(f"Checkpoint saved at epoch {epoch + 1}")
                    np.save(
                        f"{config.output_dir}/history.npy", np.array(loss_logging)
                    )

    return (train_loop,)


@app.cell
def _(
    config,
    lr_scheduler,
    model,
    optimizer,
    train_dataloader,
    train_loop,
    val_dataloader,
):
    # ------------------------------------------------------------------
    # Kick off training. Wrapped so accelerator / notebook_launcher locals
    # don't leak into the marimo dataflow graph.
    # ------------------------------------------------------------------


    def _launch():
        from accelerate import notebook_launcher

        launcher_args = (
            config,
            model,
            optimizer,
            train_dataloader,
            val_dataloader,
            lr_scheduler,
        )
        notebook_launcher(train_loop, launcher_args, num_processes=1)


    _launch()
    return


@app.cell
def _(Path, config, np, plt):
    # Plot losses once a history file exists. No-op until training has saved one.
    def _plot_history():
        history_path = Path(config.output_dir) / "history.npy"
        if not history_path.exists():
            print(f"No history file yet at {history_path}. Run training first.")
            return
        losses = np.load(history_path)
        train_losses, val_losses, val_accs = [], [], []
        for row in losses:
            train_losses.append(row[0])
            val_losses.append(row[1])
            if len(row) > 2:
                val_accs.append(row[2])

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 4))
        epochs = np.arange(1, len(losses) + 1)
        ax1.plot(epochs, train_losses, marker="o", label="Training Loss")
        ax1.plot(epochs, val_losses, marker="^", label="Validation Loss")
        ax1.set_xlabel("Epoch")
        ax1.set_ylabel("Loss")
        ax1.legend()
        ax1.set_title("Training Loss by Epoch")
        ax1.grid(True)

        if val_accs:
            ax2.plot(
                epochs,
                val_accs,
                marker="s",
                color="green",
                label="Val piece accuracy",
            )
            ax2.set_xlabel("Epoch")
            ax2.set_ylabel("Accuracy")
            ax2.set_ylim(0, 1)
            ax2.legend()
            ax2.set_title("Per-square Piece Accuracy")
            ax2.grid(True)
        plt.tight_layout()
        plt.show()


    _plot_history()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Inferencing

    The cells below are **guarded**: they only do anything after a checkpoint
    exists at `config.output_dir`. On a fresh notebook they print a skip
    message rather than crashing. Once training completes, they start
    producing output.
    """)
    return


@app.cell
def _(
    Path,
    VQModel,
    config,
    device,
    display_board_tensors,
    piece_accuracy,
    torch,
    val_dataloader,
):
    # ------------------------------------------------------------------
    # Full-pipeline reconstruction demo (guarded on checkpoint existence).
    # ------------------------------------------------------------------


    def _recon_demo():
        ckpt_cfg = Path(config.output_dir) / "config.json"
        if not ckpt_cfg.exists():
            print(f"[recon demo] No checkpoint at {config.output_dir}, skipping.")
            return
        loaded = VQModel.from_pretrained(config.output_dir).to(device)
        loaded.eval()
        print(f"Model loaded; expects (B, {config.num_channels}, 8, 8) input")

        with torch.no_grad():
            for idx, batch in enumerate(val_dataloader):
                xb, yb = batch
                images = xb.permute(0, 3, 1, 2).contiguous().to(device)
                out = loaded(images).sample
                enc = loaded.encode(images).latents

                print(f"Input shape : {tuple(images.shape)}")
                print(f"Latent shape: {tuple(enc.shape)}")
                print(f"Output shape: {tuple(out.shape)}")
                print(f"Batch piece accuracy: {piece_accuracy(out, images):.4f}")

                pairs, titles = [], []
                for i in range(min(2, images.shape[0])):
                    pairs.extend([images[i], out[i]])
                    titles.extend(
                        [f"orig {i}  y={yb[i].item():.3f}", f"recon {i}"]
                    )
                display_board_tensors(
                    pairs, titles=titles, figsize=(4 * len(pairs), 4)
                )
                if idx == 0:
                    break


    _recon_demo()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Split Inferencing (encode / decode helpers)
    """)
    return


@app.cell
def _(Path, VQModel, config, device, torch):
    # ------------------------------------------------------------------
    # Load a fresh copy of the model for encode/decode helpers. Returns
    # (inference_model, encode_fn, decode_fn) if a checkpoint exists, else
    # (None, None, None). Downstream cells no-op when inference_model is None.
    # ------------------------------------------------------------------


    def _load_inference_model():
        ckpt_cfg = Path(config.output_dir) / "config.json"
        if not ckpt_cfg.exists():
            print(
                f"[inference model] No checkpoint at {config.output_dir}, skipping."
            )
            return None, None, None

        m = VQModel.from_pretrained(config.output_dir).to(device)
        m.eval()

        def encode_fn(image: torch.Tensor):
            """image: (B, C, 8, 8). Returns continuous pre-VQ latents."""
            with torch.no_grad():
                return m.encode(image, return_dict=True).latents

        def decode_fn(latents: torch.Tensor):
            """latents: output of encode_fn. Returns (B, C, 8, 8) reconstruction."""
            with torch.no_grad():
                return m.decode(latents, return_dict=True).sample

        print(
            f"Inference model loaded; expects (B, {config.num_channels}, 8, 8) input"
        )
        return m, encode_fn, decode_fn


    inference_model, encode_board, decode_latents = _load_inference_model()
    return decode_latents, encode_board, inference_model


@app.cell
def _(
    config,
    device,
    encode_board,
    inference_model,
    np,
    tqdm,
    train_dataloader,
):
    # ------------------------------------------------------------------
    # Latent statistics --- useful for whitening latents before feeding a
    # downstream diffusion / EBM head. No-op without a checkpoint.
    # ------------------------------------------------------------------


    def _compute_latent_stats():
        if inference_model is None:
            print("[latent stats] No inference model, skipping.")
            return
        means, stds = [], []
        for batch in tqdm(train_dataloader, total=len(train_dataloader)):
            xb, _yb = batch
            sample = xb.permute(0, 3, 1, 2).contiguous().to(device)
            enc = encode_board(sample)
            means.append(enc.mean().item())
            stds.append(enc.std().item())
        if not means:
            print("[latent stats] No batches.")
            return
        latents_mean = float(np.array(means).mean())
        latents_std = float(np.array(stds).mean())
        print(f"Avg Mean: {latents_mean:.6f}, Avg STD: {latents_std:.6f}")
        stats = np.array([latents_mean, latents_std])
        np.save(f"{config.output_dir}/Latent_statistics.npy", stats)
        print(stats)


    _compute_latent_stats()
    return


@app.cell
def _(
    decode_latents,
    device,
    display_board_tensors,
    encode_board,
    inference_model,
    torch,
    val_dataloader,
):
    # ------------------------------------------------------------------
    # Perturb a latent with a bit of noise and see how recon degrades.
    # ------------------------------------------------------------------


    def _noise_demo():
        if inference_model is None:
            print("[noise demo] No inference model, skipping.")
            return
        xb, _yb = next(iter(val_dataloader))
        images = xb.permute(0, 3, 1, 2).contiguous().to(device)
        enc = encode_board(images[:1])
        print(f"Latent shape: {tuple(enc.shape)}")
        print(f"Latent mean/std: {enc.mean().item():.4f} / {enc.std().item():.4f}")

        noise_scale = 0.125
        noise = torch.randn_like(enc) * noise_scale
        perturbed = enc + noise
        dec = decode_latents(enc)
        dec_pert = decode_latents(perturbed)

        display_board_tensors(
            [images[0], dec[0], dec_pert[0]],
            titles=["original", "recon", f"recon (+noise {noise_scale})"],
            figsize=(12, 4),
        )


    _noise_demo()
    return


@app.cell
def _(device, encode_board, inference_model, val_dataloader):
    # ------------------------------------------------------------------
    # Visualize latent channels per board.
    # ------------------------------------------------------------------


    def _latent_channel_viz():
        if inference_model is None:
            print("[latent viz] No inference model, skipping.")
            return
        import matplotlib.pyplot as plt_local

        for idx, batch in enumerate(val_dataloader):
            xb, _yb = batch
            images = xb.permute(0, 3, 1, 2).contiguous().to(device)
            enc = encode_board(images[:1])
            print(f"Latent shape: {tuple(enc.shape)}")
            lat = enc[0].detach().cpu().numpy()
            n_lat = lat.shape[0]
            fig, axes = plt_local.subplots(1, n_lat, figsize=(3 * n_lat, 3))
            if n_lat == 1:
                axes = [axes]
            for ch, ax in enumerate(axes):
                ax.imshow(lat[ch], cmap="viridis")
                ax.set_title(f"latent ch {ch}")
                ax.axis("off")
            plt_local.tight_layout()
            plt_local.show()
            if idx == 1:
                break


    _latent_channel_viz()
    return


@app.cell
def _(
    decode_latents,
    device,
    display_board_tensors,
    encode_board,
    inference_model,
    val_dataloader,
):
    # ------------------------------------------------------------------
    # Interpolate between two boards' latents.
    # ------------------------------------------------------------------


    def _interpolation_demo():
        if inference_model is None:
            print("[interp demo] No inference model, skipping.")
            return
        xb, _yb = next(iter(val_dataloader))
        if xb.shape[0] < 2:
            print("[interp demo] Need at least 2 samples in a val batch.")
            return
        images = xb.permute(0, 3, 1, 2).contiguous().to(device)
        img1, img2 = images[0:1], images[1:2]
        enc1 = encode_board(img1)
        enc2 = encode_board(img2)
        middle = 0.5 * enc1 + 0.5 * enc2
        mid_recon = decode_latents(middle)

        display_board_tensors(
            [img1[0], img2[0], mid_recon[0]],
            titles=["board A", "board B", "decode(1/2 A + 1/2 B)"],
            figsize=(12, 4),
        )


    _interpolation_demo()
    return


if __name__ == "__main__":
    app.run()
