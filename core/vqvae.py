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
    # core/vqvae.py — VQ-VAE Architecture

    This notebook defines the `diffusers.VQModel` configuration for the chess board
    VQ-VAE and the chess-specific reconstruction loss used in Stage 0 pretraining.

    The VQ-VAE takes an **8×8×18** board tensor as input and produces a **4×4×8**
    latent feature map, using two ResNet down/up blocks at widths 64 and 128,
    with a 1024-entry codebook.

    After Stage 0 training, only the encoder and `quant_conv` are used downstream —
    the codebook, decoder, and `post_quant_conv` are saved in the Stage 0 checkpoint
    but discarded in Stages 1+.
    """)
    return


@app.cell
def _():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from diffusers import VQModel

    return F, VQModel, torch


@app.cell
def _(mo):
    mo.md("""
    ## VQModel Configuration

    Architecture parameters match the user's previously working configuration,
    with `latent_channels` bumped from 4 → 8 for a richer representation.

    | Parameter | Value | Notes |
    |---|---|---|
    | `in_channels` / `out_channels` | 18 | 12 piece + 6 metadata channels |
    | `down_block_types` | `(DownEncoderBlock2D, DownEncoderBlock2D)` | Two 2× downsamples: 8×8 → 4×4 |
    | `up_block_types` | `(UpDecoderBlock2D, UpDecoderBlock2D)` | Symmetric decoder |
    | `block_out_channels` | `(64, 128)` | Width at each block level |
    | `layers_per_block` | 2 | ResNet layers per block |
    | `mid_block_add_attention` | True | Self-attention at bottleneck |
    | `latent_channels` | **8** | Bumped from 4; 4×4×8 latent |
    | `num_vq_embeddings` | 1024 | Codebook size |
    | `norm_type` | `group` | GroupNorm |
    | `norm_num_groups` | 8 | Groups for GroupNorm |
    | `force_upcast` | False | No fp32 upcasting needed |
    | `lookup_from_codebook` | True | Straight-through codebook lookup |
    """)
    return


@app.cell
def _(VQModel):
    def build_vqvae() -> VQModel:
        """
        Instantiate the chess VQ-VAE using diffusers.VQModel.

        Input:  (B, 18, 8, 8)  — 18-channel board tensor
        Latent: (B,  8, 4, 4)  — after two 2× downsamples
        Output: (B, 18, 8, 8)  — reconstructed board logits

        Only the encoder + quant_conv are used downstream (Stages 1+).
        The decoder, codebook, and post_quant_conv are saved in the
        Stage 0 checkpoint but discarded after that.
        """
        model = VQModel(
            in_channels=18,
            out_channels=18,
            down_block_types=("DownEncoderBlock2D", "DownEncoderBlock2D"),
            up_block_types=("UpDecoderBlock2D", "UpDecoderBlock2D"),
            block_out_channels=(64, 128),
            layers_per_block=2,
            mid_block_add_attention=True,
            latent_channels=8,           # bumped from 4 → 8 for richer representation
            num_vq_embeddings=1024,
            norm_type="group",
            norm_num_groups=8,
            force_upcast=False,
            lookup_from_codebook=True,
        )
        return model

    return (build_vqvae,)


@app.cell
def _(mo):
    mo.md("""
    ## Chess-Specific Reconstruction Loss

    A weighted combination of four terms:

    | Term | Weight | Description |
    |---|---|---|
    | Cross-entropy (piece) | 1.0 | 13-class softmax (12 pieces + empty) per square |
    | MSE (stabilizer) | 0.25 | Raw MSE on all 18 output channels for early-training stability |
    | BCE (metadata) | 0.5 | Binary cross-entropy on channels 12–17 (side-to-move, castling, en passant) |
    | Commitment loss | 1.0 | VQ codebook commitment loss returned by `VQModel` |

    The **empty-square logit** for the piece cross-entropy is computed as
    `−max(piece_channels)` so that a square with no piece gets a strong empty signal.
    """)
    return


@app.cell
def _(F, torch):
    def chess_reconstruction_loss(
        recon_logits: "torch.Tensor",   # (B, 18, 8, 8) — raw output from VQModel
        target: "torch.Tensor",          # (B, 18, 8, 8) — clean board tensor
        vq_loss: "torch.Tensor",         # scalar commitment loss from VQModel
        w_piece: float = 1.0,
        w_mse: float = 0.25,
        w_meta: float = 0.5,
        w_vq: float = 1.0,
    ) -> "tuple[torch.Tensor, dict]":
        """
        Compute the weighted chess reconstruction loss.

        Args:
            recon_logits: Raw decoder output, shape (B, 18, 8, 8).
            target:       Clean board tensor, shape (B, 18, 8, 8).
            vq_loss:      VQ commitment loss scalar from VQModel forward.
            w_piece:      Weight for cross-entropy piece loss  (default 1.0).
            w_mse:        Weight for MSE stabilizer            (default 0.25).
            w_meta:       Weight for metadata BCE loss         (default 0.5).
            w_vq:         Weight for VQ commitment loss        (default 1.0).

        Returns:
            total_loss: Scalar weighted sum.
            components: Dict with individual loss values for logging.
        """
        # ── 1. Piece cross-entropy — channels 0–11, 13-class (12 pieces + empty) ──
        piece_logits = recon_logits[:, :12, :, :]   # (B, 12, 8, 8)
        piece_target = target[:, :12, :, :]          # (B, 12, 8, 8)  binary 0/1

        # Build empty-square logit: −max over piece channels, shape (B, 1, 8, 8)
        empty_logit = -piece_logits.max(dim=1, keepdim=True).values  # (B, 1, 8, 8)

        # 13-class logits: [12 piece channels | empty logit], (B, 13, 8, 8)
        logits_13 = torch.cat([piece_logits, empty_logit], dim=1)

        # Target class index: argmax over piece channels; squares where all piece
        # channels are zero get class 12 (empty).
        piece_class = piece_target.argmax(dim=1)           # (B, 8, 8) — values 0..11
        empty_mask = piece_target.sum(dim=1) < 0.5         # (B, 8, 8) — True if empty square
        piece_class[empty_mask] = 12                        # class 12 = empty

        # Cross-entropy over flattened (B*H*W,) positions
        logits_flat = logits_13.permute(0, 2, 3, 1).reshape(-1, 13)  # (B*64, 13)
        target_flat = piece_class.reshape(-1)                          # (B*64,)
        loss_piece = F.cross_entropy(logits_flat, target_flat)

        # ── 2. MSE stabilizer — all 18 channels ──
        loss_mse = F.mse_loss(recon_logits, target)

        # ── 3. Metadata BCE — channels 12–17 ──
        meta_logits = recon_logits[:, 12:, :, :]   # (B, 6, 8, 8)
        meta_target = target[:, 12:, :, :]          # (B, 6, 8, 8)  binary 0/1
        loss_meta = F.binary_cross_entropy_with_logits(meta_logits, meta_target)

        # ── 4. VQ commitment loss (returned by VQModel forward) ──
        loss_vq = vq_loss

        total = (
            w_piece * loss_piece
            + w_mse   * loss_mse
            + w_meta  * loss_meta
            + w_vq    * loss_vq
        )

        components = {
            "loss_piece": loss_piece.item(),
            "loss_mse":   loss_mse.item(),
            "loss_meta":  loss_meta.item(),
            "loss_vq":    loss_vq.item(),
            "loss_total": total.item(),
        }
        return total, components

    return (chess_reconstruction_loss,)


@app.cell
def _(mo):
    mo.md("""
    ## Encoder Extraction Helpers

    After Stage 0, downstream stages (energy model, Stage 1+) need only the
    encoder + `quant_conv`. This helper extracts them from a full VQ-VAE and
    optionally freezes the **first** `DownEncoderBlock2D` (index 0) plus `conv_in`,
    leaving the **second** block (index 1) trainable — matching the spec's
    "first block frozen, last block trainable" intent.
    """)
    return


@app.cell
def _(VQModel, build_vqvae, torch):
    def extract_encoder(
        vqvae: VQModel,
        freeze_first_block: bool = True,
    ) -> "tuple[nn.Module, nn.Module]":
        """
        Extract encoder and quant_conv from a trained VQModel.

        Args:
            vqvae:              A trained diffusers.VQModel instance.
            freeze_first_block: If True, freeze DownEncoderBlock2D[0] and conv_in.
                                Block[1] (the last down block) stays trainable.

        Returns:
            encoder:    vqvae.encoder  (nn.Module)
            quant_conv: vqvae.quant_conv (nn.Module)
        """
        encoder = vqvae.encoder
        quant_conv = vqvae.quant_conv

        if freeze_first_block:
            # Freeze initial projection conv
            for param in encoder.conv_in.parameters():
                param.requires_grad = False
            # Freeze first DownEncoderBlock2D (index 0)
            for param in encoder.down_blocks[0].parameters():
                param.requires_grad = False
            # Block 1 (last DownEncoderBlock2D) and mid_block remain trainable

        return encoder, quant_conv


    def load_encoder_from_checkpoint(
        checkpoint_path: str,
        freeze_first_block: bool = True,
        device: str = "cpu",
    ) -> "tuple[nn.Module, nn.Module]":
        """
        Load encoder + quant_conv weights from a Stage 0 checkpoint file.

        Args:
            checkpoint_path:    Path to checkpoints/vqvae.pt
            freeze_first_block: Whether to freeze the first encoder block.
            device:             Torch device string, e.g. "cuda" or "cpu".

        Returns:
            encoder, quant_conv — initialised from VQ-VAE weights, ready for
            copying into the online and JEPA target encoders in Stage 1.
        """
        vqvae = build_vqvae()   # noqa: F821 — defined earlier in this notebook
        ckpt = torch.load(checkpoint_path, map_location=device)
        vqvae.load_state_dict(ckpt["model_state_dict"])
        vqvae.to(device)
        vqvae.eval()
        return extract_encoder(vqvae, freeze_first_block=freeze_first_block)

    return (extract_encoder,)


@app.cell
def _(mo):
    mo.md("""
    ## Sanity Checks *(cheap — no file writes, safe on import)*
    """)
    return


@app.cell
def _(build_vqvae, chess_reconstruction_loss, mo, torch):
    # ── Forward-pass shape check ──
    _model = build_vqvae()
    _model.eval()

    _x = torch.zeros(2, 18, 8, 8)   # batch of 2 blank boards

    with torch.no_grad():
        _out = _model(_x, return_dict=False)

    # VQModel returns (sample, emb_loss, ...) when return_dict=False
    _recon, _vq_loss = _out[0], _out[1]

    assert _recon.shape == (2, 18, 8, 8), f"Unexpected output shape: {_recon.shape}"

    _total, _comps = chess_reconstruction_loss(_recon, _x, _vq_loss)

    mo.md(
        f"""
        **Shape check passed ✓**

        | Tensor | Shape |
        |---|---|
        | Input | `{tuple(_x.shape)}` |
        | Reconstruction | `{tuple(_recon.shape)}` |
        | VQ loss | `{_vq_loss.item():.4f}` |
        | Total loss | `{_comps['loss_total']:.4f}` |

        Loss breakdown: piece=`{_comps['loss_piece']:.4f}` · mse=`{_comps['loss_mse']:.4f}` · meta=`{_comps['loss_meta']:.4f}` · vq=`{_comps['loss_vq']:.4f}`
        """
    )
    return


@app.cell
def _(build_vqvae, extract_encoder, mo):
    # ── Parameter count check ──
    _vqvae = build_vqvae()
    _enc, _qconv = extract_encoder(_vqvae, freeze_first_block=True)

    _total_params   = sum(p.numel() for p in _vqvae.parameters())
    _enc_params     = sum(p.numel() for p in _enc.parameters())
    _enc_trainable  = sum(p.numel() for p in _enc.parameters() if p.requires_grad)
    _enc_frozen     = _enc_params - _enc_trainable

    mo.md(
        f"""
        **Parameter counts ✓**

        | Component | Params |
        |---|---|
        | Full VQ-VAE | {_total_params:,} |
        | Encoder total | {_enc_params:,} |
        | Encoder trainable (last block + mid_block) | {_enc_trainable:,} |
        | Encoder frozen (first block + conv_in) | {_enc_frozen:,} |
        """
    )
    return


if __name__ == "__main__":
    app.run()
