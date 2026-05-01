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
    # core/energy.py — Energy Model Architecture

    This notebook defines the hand-written **Energy-Based Model (EBM)** used in this
    project. There is no diffusers primitive for joint-embedding energy models — this
    is one of the two novel hand-written components (the other is the inference loop).

    ## Overview

    The energy model takes a `(problem_board, candidate_trace_board)` pair and outputs
    a **single scalar energy**. Lower energy = better continuation.

    ```
    problem  (B,18,8,8) ──► online encoder  ──► flatten ──► ep  (B,128)  ─┐
                                                                             ├─► 4-way fuse (B,512) ──► MLP 512→256→128→1 ──► energy (B,1)
    trace    (B,18,8,8) ──► JEPA target enc  ──► flatten ──► et  (B,128)  ─┘
    ```

    ## JEPA Design

    Two encoder instances share the same architecture (VQModel encoder + quant_conv),
    initialized from the same Stage 0 VQ-VAE checkpoint:

    - **Online encoder** — first `DownEncoderBlock2D` frozen, second block trainable.
      Updated by gradient descent.
    - **JEPA target encoder** — parameters are an EMA of the online encoder at
      `τ_jepa = 0.999`. **Never** updated by backprop. Prevents representational collapse.

    Both the clean trace and the corrupted trace are passed through the JEPA target encoder.
    """)
    return


@app.cell
def _():
    import copy
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    return copy, nn, torch


@app.cell
def _(mo):
    mo.md("""
    ## `EncoderWrapper`

    Wraps a VQModel encoder + quant_conv into a single `nn.Module` that:
    1. Runs the encoder to produce a `(B, 8, 4, 4)` feature map.
    2. Runs `quant_conv` on that map.
    3. Flattens to a `(B, 128)` vector.

    The 4×4×8 = 128-dimensional flat vector is the board embedding fed to the fusion head.
    """)
    return


@app.cell
def _(nn):
    class EncoderWrapper(nn.Module):
        """
        Wraps a VQModel encoder + quant_conv into a flat-embedding module.

        Forward:
            board  (B, 18, 8, 8)  →  embedding  (B, 128)

        The 4×4×8 = 128-dim embedding comes from:
            encoder(board)   → (B, 8, 4, 4)   [two 2× downsamples]
            quant_conv(feat) → (B, 8, 4, 4)
            flatten          → (B, 128)
        """

        def __init__(self, encoder: nn.Module, quant_conv: nn.Module):
            super().__init__()
            self.encoder = encoder
            self.quant_conv = quant_conv

        def forward(self, board: "torch.Tensor") -> "torch.Tensor":
            # board: (B, 18, 8, 8)
            feat = self.encoder(board)          # (B, 8, 4, 4)
            feat = self.quant_conv(feat)         # (B, 8, 4, 4)
            return feat.flatten(start_dim=1)     # (B, 128)

    return (EncoderWrapper,)


@app.cell
def _(mo):
    mo.md("""
    ## `FusionMLP`

    The 3-layer MLP that maps the 512-dim fused vector to a scalar energy.

    ### 4-way fusion

    Given online embedding `ep` and target embedding `et`, both `(B, 128)`:

    ```
    fused = cat([ep, et, ep - et, ep * et])   →  (B, 512)
    ```

    The difference `ep − et` and element-wise product `ep ⊙ et` give the head
    explicit *compare* signals, so it doesn't need to learn subtraction/multiplication
    from scratch inside the MLP.

    ### MLP

    ```
    512 → LayerNorm → Linear(512, 256) → GELU
        → LayerNorm → Linear(256, 128) → GELU
        → LayerNorm → Linear(128,   1)
    ```

    The output is an **unbounded scalar** — no sigmoid/tanh — so the margin ranking
    loss can push energies apart freely.
    """)
    return


@app.cell
def _(nn, torch):
    class FusionMLP(nn.Module):
        """
        4-way fusion head: (ep, et) → scalar energy.

        ep, et: (B, 128)  board embeddings from online / target encoder
        output: (B, 1)    scalar energy (lower = better continuation)
        """

        def __init__(self, embed_dim: int = 128):
            super().__init__()
            fused_dim = embed_dim * 4   # cat([ep, et, ep-et, ep*et]) = 512

            self.mlp = nn.Sequential(
                nn.LayerNorm(fused_dim),
                nn.Linear(fused_dim, 256),
                nn.GELU(),
                nn.LayerNorm(256),
                nn.Linear(256, 128),
                nn.GELU(),
                nn.LayerNorm(128),
                nn.Linear(128, 1),
            )

        def forward(self, ep: "torch.Tensor", et: "torch.Tensor") -> "torch.Tensor":
            # ep, et: (B, 128)
            fused = torch.cat([ep, et, ep - et, ep * et], dim=1)  # (B, 512)
            return self.mlp(fused)                                  # (B, 1)

    return (FusionMLP,)


@app.cell
def _(mo):
    mo.md("""
    ## `EnergyModel`

    The top-level module that wires together:

    - `online_encoder`  — `EncoderWrapper` (last block trainable, first frozen)
    - `target_encoder`  — `EncoderWrapper` (JEPA EMA copy, no grad)
    - `fusion_mlp`      — `FusionMLP` (fully trainable)

    ### Trainable parameters (gradient descent)
    - `online_encoder.encoder.down_blocks[1]` (last DownEncoderBlock2D)
    - `online_encoder.encoder.mid_block`
    - `online_encoder.quant_conv`
    - All of `fusion_mlp`

    ### Non-trainable (frozen or EMA-only)
    - `online_encoder.encoder.conv_in`
    - `online_encoder.encoder.down_blocks[0]`
    - All of `target_encoder` (drifts via EMA, never via backprop)

    ### EMA update rule (call after every optimizer step)

    ```
    θ_target ← τ · θ_target + (1 − τ) · θ_online    (τ = 0.999)
    ```
    """)
    return


@app.cell
def _(EncoderWrapper, FusionMLP, copy, nn, torch):
    class EnergyModel(nn.Module):
        """
        JEPA-style joint-embedding energy model for chess boards.

        Args:
            online_encoder:  EncoderWrapper initialised from VQ-VAE weights,
                             with first block frozen.
            tau_jepa:        EMA decay for the JEPA target encoder (default 0.999).

        Usage:
            model = EnergyModel.from_encoder_wrapper(online_enc)
            energy = model(problem, candidate_trace)   # (B, 1)
            model.update_target_encoder()              # call after optimizer.step()
        """

        def __init__(
            self,
            online_encoder: EncoderWrapper,
            tau_jepa: float = 0.999,
        ):
            super().__init__()
            self.tau_jepa = tau_jepa

            # Online encoder — first block frozen (handled in EncoderWrapper/vqvae.py)
            self.online_encoder = online_encoder

            # JEPA target encoder — deep copy, no grad on any parameter
            self.target_encoder: EncoderWrapper = copy.deepcopy(online_encoder)
            for param in self.target_encoder.parameters():
                param.requires_grad = False

            # Fusion MLP — fully trainable
            self.fusion_mlp = FusionMLP(embed_dim=128)

        # ── Factory ──────────────────────────────────────────────────────────────

        @classmethod
        def from_encoder_wrapper(
            cls,
            online_encoder: EncoderWrapper,
            tau_jepa: float = 0.999,
        ) -> "EnergyModel":
            """Convenience constructor: build EnergyModel from an EncoderWrapper."""
            return cls(online_encoder=online_encoder, tau_jepa=tau_jepa)

        # ── Forward ──────────────────────────────────────────────────────────────

        def forward(
            self,
            problem: "torch.Tensor",
            candidate_trace: "torch.Tensor",
        ) -> "torch.Tensor":
            """
            Compute scalar energy for a (problem, candidate_trace) pair.

            Args:
                problem:         (B, 18, 8, 8) — problem board tensor
                candidate_trace: (B, 18, 8, 8) — clean or corrupted trace board

            Returns:
                energy: (B, 1) — scalar; lower = candidate is a better continuation
            """
            # Online encoder processes the problem board (gradient flows through last block)
            ep = self.online_encoder(problem)           # (B, 128)

            # JEPA target encoder processes the candidate trace (no gradient)
            with torch.no_grad():
                et = self.target_encoder(candidate_trace)  # (B, 128)

            # Re-enable grad on et so gradient can flow through x0 at inference
            # (the target encoder params stay frozen; only et's values are used)
            et = et.detach().requires_grad_(False)

            return self.fusion_mlp(ep, et)              # (B, 1)

        def forward_with_grad_on_trace(
            self,
            problem: "torch.Tensor",
            candidate_trace: "torch.Tensor",
        ) -> "torch.Tensor":
            """
            Variant used during **inference energy refinement**.

            Runs the target encoder WITHOUT torch.no_grad() so that gradients
            w.r.t. `candidate_trace` (x̂₀) can flow back through the full graph.
            The target encoder parameters themselves are still frozen (requires_grad=False),
            so no weights are updated — only ∂E/∂x̂₀ is computed.

            Args:
                problem:         (B, 18, 18, 8) — problem board (fixed during inference)
                candidate_trace: (B, 18,  8, 8) — x̂₀ from diffusion model

            Returns:
                energy: (B, 1) scalar
            """
            ep = self.online_encoder(problem)           # (B, 128)
            et = self.target_encoder(candidate_trace)   # (B, 128)  grad flows through here
            return self.fusion_mlp(ep, et)              # (B, 1)

        # ── JEPA EMA update ──────────────────────────────────────────────────────

        @torch.no_grad()
        def update_target_encoder(self) -> None:
            """
            EMA update: θ_target ← τ · θ_target + (1 − τ) · θ_online

            Call this **after every optimizer.step()** in the training loop.
            τ = self.tau_jepa (default 0.999).
            """
            for param_online, param_target in zip(
                self.online_encoder.parameters(),
                self.target_encoder.parameters(),
            ):
                param_target.data.mul_(self.tau_jepa).add_(
                    param_online.data, alpha=1.0 - self.tau_jepa
                )

        # ── Utility ──────────────────────────────────────────────────────────────

        def trainable_parameters(self):
            """
            Returns only the parameters that should be passed to the optimizer:
            - online_encoder (last block + mid_block + quant_conv only — first block frozen)
            - fusion_mlp (all parameters)

            The target encoder is intentionally excluded.
            """
            return (
                list(p for p in self.online_encoder.parameters() if p.requires_grad)
                + list(self.fusion_mlp.parameters())
            )

    return (EnergyModel,)


@app.cell
def _(mo):
    mo.md("""
    ## `margin_ranking_loss`

    Stage 1 training loss: pairwise margin ranking loss.

    ```
    L = mean( max(0,  m + E(problem, clean_trace) − E(problem, corrupted_trace)) )
    ```

    Lower energy for clean traces, higher energy for corrupted ones.
    The margin `m` starts at 1.0 (spec default).

    Also returns the **margin satisfaction rate** — fraction of pairs where
    `E_clean + m < E_corrupted` — used as the Stage 1 validation metric.
    """)
    return


@app.cell
def _(torch):
    def margin_ranking_loss(
        e_clean: "torch.Tensor",      # (B, 1) energy for (problem, clean_trace)
        e_corrupted: "torch.Tensor",  # (B, 1) energy for (problem, corrupted_trace)
        margin: float = 1.0,
    ) -> "tuple[torch.Tensor, float]":
        """
        Pairwise margin ranking loss for the energy model.

        L = mean( max(0,  m + E_clean − E_corrupted) )

        Args:
            e_clean:     (B, 1) scalar energies for (problem, clean_trace) pairs.
            e_corrupted: (B, 1) scalar energies for (problem, corrupted_trace) pairs.
            margin:      Margin m (default 1.0 per spec).

        Returns:
            loss:                   Scalar loss tensor (differentiable).
            margin_satisfaction:    Float in [0, 1] — fraction of pairs satisfying
                                    E_clean + m < E_corrupted. Used for validation logging.
        """
        # Both are (B, 1) — squeeze to (B,) for clean arithmetic
        e_c = e_clean.squeeze(1)       # (B,)
        e_r = e_corrupted.squeeze(1)   # (B,)

        loss = torch.clamp(margin + e_c - e_r, min=0.0).mean()

        with torch.no_grad():
            satisfied = (e_c + margin < e_r).float().mean().item()

        return loss, satisfied

    return (margin_ranking_loss,)


@app.cell
def _(mo):
    mo.md("""
    ## `build_energy_model`

    Factory function that constructs a fully wired `EnergyModel` from a Stage 0
    VQ-VAE checkpoint path. This is the entry point used by the training notebooks.

    ```python
    from core.energy import build_energy_model
    model = build_energy_model("checkpoints/vqvae.pt", device="cuda")
    ```
    """)
    return


@app.cell
def _(EncoderWrapper, EnergyModel, torch):
    def build_energy_model(
        vqvae_checkpoint_path: str,
        tau_jepa: float = 0.999,
        device: str = "cpu",
    ) -> EnergyModel:
        """
        Build a fully wired EnergyModel from a Stage 0 VQ-VAE checkpoint.

        Steps:
        1. Load the full VQModel from `vqvae_checkpoint_path`.
        2. Extract encoder + quant_conv, freeze first DownEncoderBlock2D + conv_in.
        3. Wrap in EncoderWrapper.
        4. Construct EnergyModel (which deep-copies the wrapper for the target encoder).
        5. Move to `device`.

        Args:
            vqvae_checkpoint_path: Path to checkpoints/vqvae.pt (Stage 0 output).
            tau_jepa:              JEPA EMA decay (default 0.999).
            device:                Torch device string.

        Returns:
            EnergyModel ready for Stage 1 training.
        """
        # Import here to avoid circular dependency at module level
        from core.vqvae import build_vqvae  # type: ignore[import]

        vqvae = build_vqvae()
        ckpt = torch.load(vqvae_checkpoint_path, map_location=device)
        vqvae.load_state_dict(ckpt["model_state_dict"])
        vqvae.to(device)
        vqvae.eval()

        # Freeze first block + conv_in; last block stays trainable
        encoder = vqvae.encoder
        quant_conv = vqvae.quant_conv

        for param in encoder.conv_in.parameters():
            param.requires_grad = False
        for param in encoder.down_blocks[0].parameters():
            param.requires_grad = False

        online_enc = EncoderWrapper(encoder, quant_conv)
        model = EnergyModel(online_encoder=online_enc, tau_jepa=tau_jepa)
        model.to(device)
        return model

    return


@app.cell
def _(mo):
    mo.md("""
    ## Sanity Checks *(cheap — no file writes, safe on import)*
    """)
    return


@app.cell
def _(EnergyModel, FusionMLP, margin_ranking_loss, mo, torch):
    # ── Build a minimal EnergyModel from scratch (no checkpoint needed) ──
    # Simulate an encoder as a tiny stand-in so the sanity check is self-contained.
    import torch.nn as _nn

    class _TinyEncoder(_nn.Module):
        """Minimal stand-in encoder: (B,18,8,8) → (B,128) via adaptive pool + linear."""
        def __init__(self):
            super().__init__()
            self.proj = _nn.Linear(18 * 8 * 8, 128)
        def forward(self, x):
            return self.proj(x.flatten(1))

    # Wrap in EncoderWrapper-compatible interface by subclassing
    class _StubEncoderWrapper(_nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = _TinyEncoder()
        def forward(self, x):
            return self.enc(x)
        def parameters(self, recurse=True):
            return self.enc.parameters(recurse)

    # Build energy model using FusionMLP directly to keep test self-contained
    _fusion = FusionMLP(embed_dim=128)
    _online = _StubEncoderWrapper()
    _target = _StubEncoderWrapper()
    for _p in _target.parameters():
        _p.requires_grad = False

    # ── Forward pass shape check ──
    _B = 4
    _problem = torch.randn(_B, 18, 8, 8)
    _clean   = torch.randn(_B, 18, 8, 8)
    _corrupt = torch.randn(_B, 18, 8, 8)

    _ep = _online(_problem)                         # (B, 128)
    _et_clean   = _target(_clean)                   # (B, 128)
    _et_corrupt = _target(_corrupt)                 # (B, 128)

    _e_clean   = _fusion(_ep, _et_clean)            # (B, 1)
    _e_corrupt = _fusion(_ep, _et_corrupt)          # (B, 1)

    assert _e_clean.shape   == (_B, 1), f"Expected ({_B},1), got {_e_clean.shape}"
    assert _e_corrupt.shape == (_B, 1), f"Expected ({_B},1), got {_e_corrupt.shape}"

    # ── Loss check ──
    _loss, _sat = margin_ranking_loss(_e_clean, _e_corrupt, margin=1.0)
    assert _loss.shape == torch.Size([]), "Loss should be a scalar"

    # ── EMA update check (using real EnergyModel with stub encoders) ──
    # Patch EncoderWrapper to accept the stub
    _em = EnergyModel.__new__(EnergyModel)
    _nn.Module.__init__(_em)
    _em.tau_jepa = 0.999
    _em.online_encoder = _online
    import copy as _copy
    _em.target_encoder = _copy.deepcopy(_online)
    for _p in _em.target_encoder.parameters():
        _p.requires_grad = False
    _em.fusion_mlp = _fusion

    _target_params_before = [p.data.clone() for p in _em.target_encoder.parameters()]
    _em.update_target_encoder()
    _target_params_after  = [p.data.clone() for p in _em.target_encoder.parameters()]
    _ema_moved = any(not torch.equal(b, a) for b, a in zip(_target_params_before, _target_params_after))

    mo.md(
        f"""
        **Sanity checks passed ✓**

        | Check | Result |
        |---|---|
        | `e_clean` shape | `{tuple(_e_clean.shape)}` |
        | `e_corrupted` shape | `{tuple(_e_corrupt.shape)}` |
        | Margin ranking loss | `{_loss.item():.4f}` (scalar ✓) |
        | Margin satisfaction rate | `{_sat:.2%}` |
        | EMA target moved after update | `{"✓" if _ema_moved else "✗ — EMA did not move!"}` |
        """
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## Parameter Summary

    | Component | Grad? | Updated by |
    |---|---|---|
    | `online_encoder.encoder.conv_in` | ✗ | Frozen |
    | `online_encoder.encoder.down_blocks[0]` | ✗ | Frozen |
    | `online_encoder.encoder.down_blocks[1]` | ✓ | AdamW |
    | `online_encoder.encoder.mid_block` | ✓ | AdamW |
    | `online_encoder.quant_conv` | ✓ | AdamW |
    | `fusion_mlp` | ✓ | AdamW |
    | `target_encoder` (all) | ✗ | JEPA EMA (τ=0.999) |

    The inference EMA (τ=0.9999) is managed externally by the training notebooks
    via `diffusers.training_utils.EMAModel` — it is not part of this architecture file.
    """)
    return


if __name__ == "__main__":
    app.run()
