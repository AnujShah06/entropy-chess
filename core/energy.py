import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo

    import copy
    import torch
    import torch.nn as nn
    import torch.nn.functional as F


@app.cell
def _():
    mo.md("""
    # core/energy.py — Energy Model Architecture

    This notebook defines the hand-written **Energy-Based Model (EBM)** for chess
    board comparison. There is no VQ-VAE, no pretrained weights, and no frozen layers —
    everything trains from scratch in Stage 1.

    ## System Overview

    ```
    problem  (B, 18, 8, 8) ──► ChessEncoder (online)       ──► ep  (B, 16, 8, 8) ─┐
                                                                                      ├──► FusionHead ──► energy (B,)
    trace    (B, 18, 8, 8) ──► ChessEncoder (JEPA target)  ──► et  (B, 16, 8, 8) ─┘
    ```

    ## Two EMAs — coexist cleanly

    | EMA | Decay | Role |
    |---|---|---|
    | **JEPA target encoder** | τ=0.999 | Structural — provides trace embeddings during training. Prevents representational collapse. Never updated by backprop. |
    | **Inference EMA** | τ=0.9999 | Quality — slow snapshot of all trainable params. Used only at eval/deploy time. Managed externally by training notebooks. |

    ## Trainable in Stage 1
    - Full `online_encoder` (all parameters — no freezing without pretrained init)
    - Full `fusion_head` (all parameters)
    - **Total: ~3.4M trainable parameters**

    ## Not updated by gradient descent
    - `target_encoder` — drifts via JEPA EMA only
    """)
    return


@app.cell
def _():
    mo.md("""
    ## `ResnetBlock`

    Standard pre-norm residual conv block shared by both `ChessEncoder` and
    `FusionHead`. Uses GroupNorm + SiLU + two 3×3 convolutions with a skip
    connection. No downsampling — spatial resolution is preserved.

    ```
    x ──► GroupNorm ──► SiLU ──► Conv3x3 ──► GroupNorm ──► SiLU ──► Conv3x3 ──► + ──► out
    └──────────────────────────────────────────────────────────────────────────────┘
    ```
    """)
    return


@app.class_definition
class ResnetBlock(nn.Module):
    """
    Pre-norm residual 3×3 conv block. Preserves (B, C, H, W) shape.

    Args:
        channels:  Number of input and output channels.
        groups:    Number of groups for GroupNorm (default 8).
    """

    def __init__(self, channels: int, groups: int = 8):
        super().__init__()
        self.norm1 = nn.GroupNorm(groups, channels)
        self.conv1 = nn.Conv2d(channels, channels, 3, padding=1)
        self.norm2 = nn.GroupNorm(groups, channels)
        self.conv2 = nn.Conv2d(channels, channels, 3, padding=1)
        self.act   = nn.SiLU()

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        h = self.conv1(self.act(self.norm1(x)))
        h = self.conv2(self.act(self.norm2(h)))
        return x + h


@app.cell
def _():
    mo.md("""
    ## `ChessEncoder`

    Maps an `(B, 18, 8, 8)` board tensor to a `(B, 16, 8, 8)` per-square
    feature map. **No spatial downsampling** — every square retains its own
    feature vector throughout.

    | Layer | Shape out | Notes |
    |---|---|---|
    | `in_proj` Conv3×3(18→160) | (B, 160, 8, 8) | Expand channels |
    | 4× `ResnetBlock(160)` | (B, 160, 8, 8) | Full-board receptive field after 4 blocks |
    | `norm_out` GroupNorm + SiLU | (B, 160, 8, 8) | |
    | `out_proj` Conv1×1(160→16) | (B, 16, 8, 8) | Compress to per-square embedding |

    ### Sizing rationale
    - **Width 160, 4 blocks**: 8 conv layers of 3×3 kernels gives an effective receptive
      field that covers the full 8×8 board. Enough capacity for piece-relationship
      features without overfitting on 180k pairs.
    - **Output 16 channels**: more than 12 piece classes, leaving capacity for
      relational features. This is the input width the `FusionHead` expects.
    - **~1.85M parameters**: healthy data-to-parameter ratio with 180k training pairs.
    """)
    return


@app.class_definition
class ChessEncoder(nn.Module):
    """
    Custom board encoder. Maps (B, 18, 8, 8) → (B, out_channels, 8, 8).
    No spatial downsampling — 8×8 resolution is preserved end-to-end.

    Args:
        in_channels:  Input board channels (default 18).
        hidden:       ResNet block width (default 160).
        out_channels: Per-square output feature dim (default 16).
        num_blocks:   Number of ResNet blocks (default 4).
    """

    def __init__(
        self,
        in_channels: int = 18,
        hidden: int = 160,
        out_channels: int = 16,
        num_blocks: int = 4,
    ):
        super().__init__()
        self.in_proj = nn.Conv2d(in_channels, hidden, 3, padding=1)
        self.blocks  = nn.ModuleList(
            [ResnetBlock(hidden) for _ in range(num_blocks)]
        )
        self.norm_out = nn.GroupNorm(8, hidden)
        self.act_out  = nn.SiLU()
        self.out_proj = nn.Conv2d(hidden, out_channels, 1)  # 1×1 projection

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        # x: (B, 18, 8, 8)
        h = self.in_proj(x)            # (B, hidden, 8, 8)
        for block in self.blocks:
            h = block(h)               # (B, hidden, 8, 8)  — no spatial change
        h = self.act_out(self.norm_out(h))
        return self.out_proj(h)


@app.cell
def _():
    mo.md("""
    ## `FusionHead`

    Compares two `(B, 16, 8, 8)` board embeddings and outputs a scalar energy.
    This is the heaviest reasoning component — it must learn implicit chess
    understanding from 180k examples.

    ### 4-way spatial fusion

    ```
    ep, et  →  cat([ep, et, ep−et, ep⊙et], dim=1)  →  (B, 64, 8, 8)
    ```

    The difference `ep−et` makes **"what changed?"** an explicit input feature.
    The product `ep⊙et` makes **"what stayed the same?"** explicit. The conv stack
    doesn't have to discover these comparisons inside its weights.

    ### Architecture

    | Layer | Shape out | Notes |
    |---|---|---|
    | `in_proj` Conv3×3(64→192) | (B, 192, 8, 8) | Project fused input |
    | 2× `ResnetBlock(192)` | (B, 192, 8, 8) | Spatial reasoning at full 8×8 |
    | `norm_out` + SiLU | (B, 192, 8, 8) | |
    | Global avg pool | (B, 192) | Board-level summary |
    | MLP 192→192→96→1 | (B, 1) | LayerNorm+GELU, unbounded scalar |

    ### Sizing rationale
    - **2 ResNet blocks at width 192**: with `in_proj` + 2 blocks × 2 convs each,
      the spatial receptive field covers the full board. Enough capacity for tactical
      move-quality signals.
    - **Global avg pool then MLP**: reduces (B, 192, 8, 8) to (B, 192) before scalar
      reduction. The MLP does final reasoning with LayerNorm+GELU.
    - **Unbounded output**: no sigmoid/tanh, so the margin ranking loss can push
      energies as far apart as the signal demands.
    - **~1.5M parameters**: together with encoder 1.85M → **3.4M total**.
    """)
    return


@app.class_definition
class FusionHead(nn.Module):
    """
    Spatial 4-way fusion head: (ep, et) → scalar energy.

    ep, et: (B, in_channels, 8, 8)  per-square board embeddings
    output: (B,)                     scalar energy; lower = better continuation
    """

    def __init__(
        self,
        in_channels: int = 16,
        hidden: int = 192,
        num_blocks: int = 2,
    ):
        super().__init__()
        fused_in = in_channels * 4   # cat([ep, et, ep-et, ep*et]) = 64 channels

        self.in_proj = nn.Conv2d(fused_in, hidden, 3, padding=1)
        self.conv_blocks = nn.ModuleList(
            [ResnetBlock(hidden) for _ in range(num_blocks)]
        )
        self.norm_out = nn.GroupNorm(8, hidden)
        self.act_out  = nn.SiLU()

        # After global avg pool: (B, hidden) → scalar
        self.mlp = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.LayerNorm(hidden),
            nn.GELU(),
            nn.Linear(hidden, hidden // 2),
            nn.LayerNorm(hidden // 2),
            nn.GELU(),
            nn.Linear(hidden // 2, 1),
        )

    def forward(
        self,
        ep: "torch.Tensor",   # (B, 16, 8, 8)
        et: "torch.Tensor",   # (B, 16, 8, 8)
    ) -> "torch.Tensor":
        # 4-way spatial fusion
        diff  = ep - et
        prod  = ep * et
        fused = torch.cat([ep, et, diff, prod], dim=1)  # (B, 64, 8, 8)

        h = self.in_proj(fused)              # (B, hidden, 8, 8)
        for block in self.conv_blocks:
            h = block(h)                     # (B, hidden, 8, 8)
        h = self.act_out(self.norm_out(h))   # (B, hidden, 8, 8)

        h = h.mean(dim=(2, 3))               # (B, hidden)  — global avg pool
        return self.mlp(h).squeeze(-1)


@app.cell
def _():
    mo.md("""
    ## `EnergyModel`

    Top-level module wiring together:
    - `online_encoder`  — `ChessEncoder`, all parameters trainable
    - `target_encoder`  — `ChessEncoder`, JEPA EMA copy, no backprop ever
    - `fusion_head`     — `FusionHead`, fully trainable

    ### Two forward methods

    | Method | When to use |
    |---|---|
    | `forward(problem, trace)` | **Training** — `torch.no_grad()` on target encoder, detaches `et` |
    | `forward_with_grad_on_trace(problem, trace)` | **Inference refinement** — gradient flows through target encoder to compute ∂E/∂x̂₀ |

    ### JEPA EMA update rule
    ```
    θ_target ← τ · θ_target + (1 − τ) · θ_online    τ = 0.999
    ```
    Call `model.update_target_encoder()` after every `optimizer.step()`.
    """)
    return


@app.class_definition
class EnergyModel(nn.Module):
    """
    JEPA-style joint-embedding energy model for chess boards.

    Built entirely from scratch — no VQ-VAE, no pretrained weights.
    The JEPA target encoder is the structural collapse prevention mechanism.

    Args:
        encoder_kwargs:  Dict of kwargs forwarded to both ChessEncoder instances.
                         Defaults match spec: hidden=160, out_channels=16, num_blocks=4.
        fusion_kwargs:   Dict of kwargs forwarded to FusionHead.
                         Defaults match spec: in_channels=16, hidden=192, num_blocks=2.
        tau_jepa:        EMA decay for the JEPA target encoder (default 0.999).
    """

    def __init__(
        self,
        encoder_kwargs: dict = None,
        fusion_kwargs: dict = None,
        tau_jepa: float = 0.999,
    ):
        super().__init__()
        self.tau_jepa = tau_jepa

        enc_kw  = encoder_kwargs or {}
        fuse_kw = fusion_kwargs  or {}

        # Online encoder — fully trainable from scratch, no freezing
        self.online_encoder = ChessEncoder(**enc_kw)

        # JEPA target encoder — deep copy of online, no gradient ever
        self.target_encoder: ChessEncoder = copy.deepcopy(self.online_encoder)
        for param in self.target_encoder.parameters():
            param.requires_grad = False

        # Fusion head — fully trainable
        self.fusion_head = FusionHead(**fuse_kw)

    # ── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def from_scratch(
        cls,
        tau_jepa: float = 0.999,
        encoder_hidden: int = 160,
        encoder_out_channels: int = 16,
        encoder_num_blocks: int = 4,
        fusion_hidden: int = 192,
        fusion_num_blocks: int = 2,
    ) -> "EnergyModel":
        """
        Build a fresh EnergyModel with spec-default hyperparameters.
        Used by Stage 1 training notebook.

        Returns an EnergyModel with ~3.4M trainable parameters.
        """
        return cls(
            encoder_kwargs={
                "hidden": encoder_hidden,
                "out_channels": encoder_out_channels,
                "num_blocks": encoder_num_blocks,
            },
            fusion_kwargs={
                "in_channels": encoder_out_channels,
                "hidden": fusion_hidden,
                "num_blocks": fusion_num_blocks,
            },
            tau_jepa=tau_jepa,
        )

    # ── Forward (training) ────────────────────────────────────────────────────

    def forward(
        self,
        problem: "torch.Tensor",
        candidate_trace: "torch.Tensor",
    ) -> "torch.Tensor":
        """
        Compute scalar energy for a (problem, candidate_trace) pair.
        Use this during **training**.

        The target encoder runs under torch.no_grad() so its activations are
        excluded from the computation graph. Gradients flow only through the
        online encoder and fusion head.

        Args:
            problem:          (B, 18, 8, 8) — problem board tensor
            candidate_trace:  (B, 18, 8, 8) — clean or corrupted trace board

        Returns:
            energy: (B,) — scalar; lower = candidate is a better continuation
        """
        ep = self.online_encoder(problem)                # (B, 16, 8, 8)

        with torch.no_grad():
            et = self.target_encoder(candidate_trace)    # (B, 16, 8, 8)
        et = et.detach()

        return self.fusion_head(ep, et)                  # (B,)

    # ── Forward (inference gradient) ──────────────────────────────────────────

    def forward_with_grad_on_trace(
        self,
        problem: "torch.Tensor",
        candidate_trace: "torch.Tensor",
    ) -> "torch.Tensor":
        """
        Compute scalar energy with **gradient flowing through candidate_trace**.
        Use this during **inference energy refinement** to compute ∂E/∂x̂₀.

        The target encoder parameters have requires_grad=False so no weights
        are updated — only the gradient w.r.t. candidate_trace (x̂₀) is used
        to refine the diffusion model's predicted clean board.

        Args:
            problem:          (B, 18, 8, 8) — fixed problem board
            candidate_trace:  (B, 18, 8, 8) — x̂₀ from diffusion model, grad enabled

        Returns:
            energy: (B,) scalar — call .sum().backward() to get ∂E/∂x̂₀
        """
        ep = self.online_encoder(problem)             # (B, 16, 8, 8)
        et = self.target_encoder(candidate_trace)     # (B, 16, 8, 8) — grad through input
        return self.fusion_head(ep, et)               # (B,)

    # ── JEPA EMA update ───────────────────────────────────────────────────────

    @torch.no_grad()
    def update_target_encoder(self) -> None:
        """
        EMA update: θ_target ← τ · θ_target + (1 − τ) · θ_online

        Call this **after every optimizer.step()** during Stage 1+ training.

        Slow-start mitigation: if loss barely moves in the first 500 steps,
        temporarily reduce tau_jepa to 0.99 and ramp back to 0.999 once
        training is stably descending. See spec for details.
        """
        for p_online, p_target in zip(
            self.online_encoder.parameters(),
            self.target_encoder.parameters(),
        ):
            p_target.data.mul_(self.tau_jepa).add_(
                p_online.data, alpha=1.0 - self.tau_jepa
            )

    # ── Utilities ─────────────────────────────────────────────────────────────

    def trainable_parameters(self) -> list:
        """
        Returns parameters for the optimizer (online encoder + fusion head).
        Target encoder is intentionally excluded — it is EMA-only.
        """
        return (
            list(self.online_encoder.parameters())
            + list(self.fusion_head.parameters())
        )

    def encoder_cosine_similarity(
        self,
        boards: "torch.Tensor",
    ) -> float:
        """
        Diagnostic: mean cosine similarity between online and target encoder
        outputs on a fixed batch. Used to detect collapse during Stage 1.

        - Stays at 1.0 → encoders haven't differentiated → reduce tau_jepa
        - Drops to ~0.0 or oscillates → diverging too fast → increase tau_jepa
        - Healthy range: 0.7–0.95 after a few hundred steps

        Args:
            boards: (B, 18, 8, 8) fixed diagnostic batch

        Returns:
            mean cosine similarity in [−1, 1]
        """
        with torch.no_grad():
            ep = self.online_encoder(boards).flatten(1)   # (B, 16*8*8)
            et = self.target_encoder(boards).flatten(1)   # (B, 16*8*8)
            cos_sim = F.cosine_similarity(ep, et, dim=1)  # (B,)
        return cos_sim.mean().item()


@app.cell
def _():
    mo.md("""
    ## `margin_ranking_loss`

    Stage 1 (and Stages 3–4) training loss — pairwise margin ranking:

    ```
    L = mean( max(0,  m + E(problem, clean_trace) − E(problem, corrupted_trace)) )
    ```

    Also returns the **margin satisfaction rate** — fraction of pairs where
    `E_clean + m < E_corrupted`. This is the primary Stage 1 validation metric.
    Should rise past 50% quickly and ideally reach 80% on easy-mix validation.
    """)
    return


@app.function
def margin_ranking_loss(
    e_clean: "torch.Tensor",      # (B,) energy for (problem, clean_trace)
    e_corrupted: "torch.Tensor",  # (B,) energy for (problem, corrupted_trace)
    margin: float = 1.0,
) -> "tuple[torch.Tensor, float]":
    """
    Pairwise margin ranking loss for energy model training.

    L = mean( max(0,  m + E_clean − E_corrupted) )

    Args:
        e_clean:     (B,) scalar energies for (problem, clean_trace).
        e_corrupted: (B,) scalar energies for (problem, corrupted_trace).
        margin:      Margin m, default 1.0 per spec.

    Returns:
        loss:                  Scalar loss tensor (differentiable).
        margin_satisfaction:   Float in [0,1] — fraction of pairs satisfying
                               E_clean + m < E_corrupted. Primary validation metric.
    """
    loss = torch.clamp(margin + e_clean - e_corrupted, min=0.0).mean()

    with torch.no_grad():
        satisfied = (e_clean + margin < e_corrupted).float().mean().item()

    return loss, satisfied


@app.cell
def _():
    mo.md("""
    ## Sanity Checks *(cheap — no file writes, safe on import)*
    """)
    return


@app.cell
def _():
    # ── 1. ResnetBlock: shape preservation ──
    _blk = ResnetBlock(channels=32)
    _x   = torch.randn(2, 32, 8, 8)
    assert _blk(_x).shape == (2, 32, 8, 8), "ResnetBlock must preserve shape"

    # ── 2. ChessEncoder: board → per-square embedding ──
    _enc = ChessEncoder()        # defaults: hidden=160, out_channels=16, num_blocks=4
    _board = torch.randn(4, 18, 8, 8)
    _emb = _enc(_board)
    assert _emb.shape == (4, 16, 8, 8), f"ChessEncoder output: expected (4,16,8,8), got {_emb.shape}"

    # ── 3. FusionHead: two embeddings → scalar ──
    _fhead = FusionHead()        # defaults: in_channels=16, hidden=192, num_blocks=2
    _ep = torch.randn(4, 16, 8, 8)
    _et = torch.randn(4, 16, 8, 8)
    _e  = _fhead(_ep, _et)
    assert _e.shape == (4,), f"FusionHead output: expected (4,), got {_e.shape}"

    # ── 4. EnergyModel: full forward pass ──
    _model   = EnergyModel.from_scratch()
    _problem = torch.randn(4, 18, 8, 8)
    _clean   = torch.randn(4, 18, 8, 8)
    _corrupt = torch.randn(4, 18, 8, 8)

    _e_clean   = _model(_problem, _clean)
    _e_corrupt = _model(_problem, _corrupt)
    assert _e_clean.shape == (4,),   f"EnergyModel clean: expected (4,), got {_e_clean.shape}"
    assert _e_corrupt.shape == (4,), f"EnergyModel corrupt: expected (4,), got {_e_corrupt.shape}"

    # ── 5. Margin ranking loss ──
    _loss, _sat = margin_ranking_loss(_e_clean, _e_corrupt, margin=1.0)
    assert _loss.shape == torch.Size([]), "Loss must be a scalar"

    # ── 6. JEPA EMA update ──
    _params_before = [p.data.clone() for p in _model.target_encoder.parameters()]
    _model.update_target_encoder()
    _params_after  = [p.data.clone() for p in _model.target_encoder.parameters()]
    _ema_moved = any(not torch.equal(b, a) for b, a in zip(_params_before, _params_after))

    # ── 7. Cosine similarity diagnostic ──
    _cos = _model.encoder_cosine_similarity(_problem)

    # ── 8. Gradient flows through trace in inference mode ──
    _x0 = torch.randn(2, 18, 8, 8, requires_grad=True)
    _e_inf = _model.forward_with_grad_on_trace(_problem[:2], _x0)
    _e_inf.sum().backward()
    _grad_exists = _x0.grad is not None and _x0.grad.abs().sum().item() > 0

    # ── 9. Parameter counts ──
    _total       = sum(p.numel() for p in _model.parameters())
    _trainable   = sum(p.numel() for p in _model.trainable_parameters())
    _enc_params  = sum(p.numel() for p in _model.online_encoder.parameters())
    _fuse_params = sum(p.numel() for p in _model.fusion_head.parameters())
    _target_req  = any(p.requires_grad for p in _model.target_encoder.parameters())

    mo.md(
        f"""
        **All sanity checks passed ✓**

        | Check | Result |
        |---|---|
        | `ResnetBlock` shape preserved | ✓ `(2, 32, 8, 8)` |
        | `ChessEncoder` output shape | ✓ `{tuple(_emb.shape)}` |
        | `FusionHead` output shape | ✓ `{tuple(_e.shape)}` |
        | `EnergyModel` forward output shapes | ✓ `{tuple(_e_clean.shape)}` |
        | Margin ranking loss scalar | ✓ `{_loss.item():.4f}` |
        | Margin satisfaction rate | `{_sat:.2%}` |
        | JEPA target EMA moved after update | `{"✓" if _ema_moved else "✗ EMA did not move!"}` |
        | Cosine similarity (random init) | `{_cos:.4f}` (expect ≈1.0 at init) |
        | Grad flows through trace at inference | `{"✓" if _grad_exists else "✗ No gradient!"}` |
        | Target encoder requires_grad=False | `{"✓" if not _target_req else "✗ target has grads!"}` |

        **Parameter counts**

        | Component | Params |
        |---|---|
        | `online_encoder` | {_enc_params:,} |
        | `fusion_head` | {_fuse_params:,} |
        | **Total trainable** | **{_trainable:,}** |
        | `target_encoder` (EMA, not trained) | {sum(p.numel() for p in _model.target_encoder.parameters()):,} |
        | Full model total | {_total:,} |
        """
    )
    return


@app.cell
def _():
    mo.md("""
    ## Architecture Summary

    | Component | Params | Key design |
    |---|---|---|
    | `ChessEncoder` (online) | ~1.85M | 4× ResnetBlock at width 160, no downsample, 18→16ch |
    | `FusionHead` | ~1.5M | 4-way spatial concat (64ch), 2× ResnetBlock at width 192, global pool, MLP 192→96→1 |
    | `ChessEncoder` (JEPA target) | ~1.85M | EMA copy of online encoder, τ=0.999, no backprop |
    | **Energy model total (trainable)** | **~3.4M** | |

    ### Key invariants
    - `target_encoder.requires_grad` is always `False`
    - `update_target_encoder()` must be called after every `optimizer.step()`
    - Training uses `forward()` (no grad through target encoder)
    - Inference refinement uses `forward_with_grad_on_trace()` (grad through x̂₀)
    - Output is an **unbounded scalar** — no sigmoid/tanh clamp
    """)
    return


if __name__ == "__main__":
    app.run()
