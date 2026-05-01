import marimo

__generated_with = "0.23.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md(r"""
    # Stage 1 — Energy Model Pretraining (Easy Mix)

    Train the energy model **from scratch** — full online problem encoder (~1.85M)
    + fusion head (~1.5M) ≈ **~3.4M trainable params** — to assign **lower energy
    to (problem, clean trace)** than to (problem, corrupted trace).

    | | |
    |---|---|
    | **Loss** | margin ranking: `relu(m + E(problem, clean) − E(problem, corrupted))` |
    | **Margin** | m = 1.0 |
    | **Dataloader** | easy mix (30% shuffle / 40% legal-move / 30% piece-swap) |
    | **JEPA target EMA** | τ_jepa = 0.999 (with 0.99 → 0.999 warmup ramp over 500 steps) |
    | **Inference EMA** | τ_inf = 0.9999 (online encoder + fusion head, fp32) |
    | **Mixed precision** | bf16 via `accelerate.Accelerator` |
    | **Output** | `checkpoints/stage1_energy.pt` |

    The diffusion model is **not** involved in this stage. The JEPA target encoder
    is updated by EMA only (never by gradients) — this is the structural collapse
    prevention without which the energy model trivially solves its loss by sending
    both branches to a constant.
    """)
    return


@app.cell
def _():
    import sys
    from pathlib import Path as _Path

    _PROJECT_ROOT = _Path(__file__).resolve().parent.parent
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))

    import copy
    import random
    from pathlib import Path

    import numpy as np
    import torch
    import torch.nn.functional as F

    from accelerate import Accelerator
    from diffusers.optimization import get_cosine_schedule_with_warmup

    return (
        Accelerator,
        F,
        Path,
        copy,
        get_cosine_schedule_with_warmup,
        np,
        random,
        torch,
    )


@app.cell
def _():
    # Project notebooks-as-modules (Pattern A from the spec).
    #
    # `train_val_indices` is the assumed name of the deterministic 95/5
    # split helper the spec says lives in `core/dataset.py` ("computed once
    # in core/dataset.py and reused identically across all stages"). Rename
    # this import if your helper is exported under a different name —
    # everything else in this notebook uses `train_indices` / `val_indices`
    # which only depend on the helper's tuple return.
    from core.dataset import (
        ChessPairDataset,
        train_val_indices,
        make_dataloader,
    )
    from core.energy import EnergyModel

    return EnergyModel, make_dataloader


@app.cell
def _():
    # Optional wandb — graceful fallback to stdout if unavailable.
    try:
        import wandb
        WANDB_AVAILABLE = True
    except ImportError:
        wandb = None
        WANDB_AVAILABLE = False
    return WANDB_AVAILABLE, wandb


@app.cell
def _():
    config = {
        # Stage identity
        "stage": 1,
        "stage_name": "stage1_energy",
        # Data
        "easy_corruption_mix": (0.30, 0.40, 0.30),  # (shuffle, legal-move, piece-swap)
        "batch_size": 64,
        "num_workers": 4,
        # Model architecture (matches Key Hyperparameters table)
        "encoder_in_channels": 18,
        "encoder_hidden": 160,
        "encoder_out_channels": 16,
        "encoder_num_blocks": 4,
        "fusion_hidden": 192,
        "fusion_num_blocks": 2,
        # Loss
        "margin": 1.0,
        # Optimization
        "learning_rate": 1e-4,
        "weight_decay": 0.01,
        "betas": (0.9, 0.999),
        "warmup_steps": 500,
        "num_epochs": 30,
        "grad_clip_norm": 1.0,
        # EMA
        "tau_jepa": 0.999,
        "tau_jepa_warmup": 0.99,           # slow-start mitigation per spec
        "tau_jepa_warmup_steps": 500,      # ramp linearly 0.99 → 0.999 over this many steps
        "tau_inf": 0.9999,
        # Precision / acceleration
        "mixed_precision": "bf16",
        # Logging cadence
        "log_every_steps": 500,
        "cosine_check_every_steps": 500,
        # Reproducibility
        "seed": 42,
        # IO
        "checkpoint_dir": "checkpoints",
        "checkpoint_filename": "stage1_energy.pt",
        # wandb
        "wandb_project": "chess-ebm-diffusion",
        "wandb_run_name": "stage1_energy",
    }
    return (config,)


@app.cell
def _(config, np, random, torch):
    # Seed Python / NumPy / PyTorch (CPU + CUDA). Per spec: speed > determinism.
    random.seed(config["seed"])
    np.random.seed(config["seed"])
    torch.manual_seed(config["seed"])
    torch.cuda.manual_seed_all(config["seed"])
    torch.use_deterministic_algorithms(False)
    torch.backends.cudnn.benchmark = True
    return


@app.cell
def _(Accelerator, config):
    accelerator = Accelerator(mixed_precision=config["mixed_precision"])
    return (accelerator,)


@app.cell
def _(WANDB_AVAILABLE, accelerator, config, wandb):
    # wandb init on the main process; fall back to stdout if anything fails.
    use_wandb = False
    if WANDB_AVAILABLE and accelerator.is_main_process:
        try:
            wandb.init(
                project=config["wandb_project"],
                name=config["wandb_run_name"],
                config=config,
            )
            use_wandb = True
        except Exception as _e:
            print(f"[wandb] init failed ({_e}); falling back to stdout logging")
    if not use_wandb and accelerator.is_main_process:
        print("[wandb] inactive — logging to stdout only")
    return (use_wandb,)


@app.cell
def _(config, make_dataloader):
    train_loader = make_dataloader(
        split="train",
        corruption_mix=config["easy_corruption_mix"],
        batch_size=config["batch_size"],
        num_workers=config["num_workers"],
        seed=config["seed"],
    )
    val_loader = make_dataloader(
        split="val",
        corruption_mix=config["easy_corruption_mix"],
        batch_size=config["batch_size"],
        num_workers=config["num_workers"],
        seed=config["seed"],
    )
    return train_loader, val_loader


@app.cell
def _(EnergyModel, config):
    # Builds online encoder + JEPA target encoder + fusion head from scratch.
    # The EnergyModel is responsible for:
    #   - copying online → target weights at init,
    #   - disabling grad on target encoder params,
    #   - routing problem through online and candidate-trace through target,
    #   - allowing gradient flow w.r.t. the candidate input (needed for
    #     inference-time energy guidance on x̂_0).
    energy_model = EnergyModel(
        encoder_kwargs={
            "in_channels": config["encoder_in_channels"],
            "hidden": config["encoder_hidden"],
            "out_channels": config["encoder_out_channels"],
            "num_blocks": config["encoder_num_blocks"],
        },
        fusion_kwargs={
            "in_channels": config["encoder_out_channels"],
            "hidden": config["fusion_hidden"],
            "num_blocks": config["fusion_num_blocks"],
        },
        # Stored on the model for reference; the actual per-step EMA decay is
        # supplied externally via `get_tau_jepa(step)` so we can ramp from
        # τ_jepa_warmup → τ_jepa over the first few hundred steps.
        tau_jepa=config["tau_jepa"],
    )
    return (energy_model,)


@app.cell
def _(accelerator, energy_model):
    # Parameter accounting sanity check. Target encoder must NOT appear in
    # the trainable count — if it does, requires_grad isn't disabled and the
    # JEPA collapse-prevention mechanism is broken.
    if accelerator.is_main_process:
        n_online = sum(p.numel() for p in energy_model.online_encoder.parameters())
        n_fusion = sum(p.numel() for p in energy_model.fusion_head.parameters())
        n_target = sum(p.numel() for p in energy_model.target_encoder.parameters())
        n_train = sum(p.numel() for p in energy_model.parameters() if p.requires_grad)
        print(f"online_encoder params : {n_online:,}")
        print(f"fusion_head    params : {n_fusion:,}")
        print(f"target encoder params : {n_target:,}  (frozen, EMA-only)")
        print(f"trainable      params : {n_train:,}")
        assert n_train == n_online + n_fusion, (
            "Trainable count mismatch — target encoder may not be properly frozen."
        )
    return


@app.cell
def _(config, energy_model, torch):
    trainable_params = [p for p in energy_model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(
        trainable_params,
        lr=config["learning_rate"],
        betas=config["betas"],
        weight_decay=config["weight_decay"],
    )
    return optimizer, trainable_params


@app.cell
def _(config, get_cosine_schedule_with_warmup, optimizer, train_loader):
    num_training_steps = config["num_epochs"] * len(train_loader)
    lr_scheduler = get_cosine_schedule_with_warmup(
        optimizer=optimizer,
        num_warmup_steps=config["warmup_steps"],
        num_training_steps=num_training_steps,
    )
    return (lr_scheduler,)


@app.cell
def _(accelerator, copy, energy_model, torch):
    # ─── Inference EMA (τ_inf = 0.9999) ───────────────────────────────────────
    # Deep copies of the trainable components, kept in fp32, frozen, and updated
    # in-place by lerp after every optimizer step. This is independent from the
    # JEPA target encoder EMA — both run as parallel readers of the live weights.
    inference_ema_online_encoder = copy.deepcopy(energy_model.online_encoder).to(
        device=accelerator.device, dtype=torch.float32
    )
    inference_ema_fusion_head = copy.deepcopy(energy_model.fusion_head).to(
        device=accelerator.device, dtype=torch.float32
    )
    for _p in inference_ema_online_encoder.parameters():
        _p.requires_grad_(False)
    for _p in inference_ema_fusion_head.parameters():
        _p.requires_grad_(False)
    inference_ema_online_encoder.eval()
    inference_ema_fusion_head.eval()
    return inference_ema_fusion_head, inference_ema_online_encoder


@app.cell
def _(torch):
    @torch.no_grad()
    def lerp_params_(target_module, source_module, tau):
        """In-place EMA: target ← τ · target + (1 − τ) · source.

        Buffers (BatchNorm running stats etc.) are copied directly. ChessEncoder
        uses GroupNorm so this is a no-op here, but kept for safety.
        """
        for p_t, p_s in zip(target_module.parameters(), source_module.parameters()):
            p_t.data.mul_(tau).add_(p_s.data.to(p_t.data.dtype), alpha=1.0 - tau)
        for b_t, b_s in zip(target_module.buffers(), source_module.buffers()):
            b_t.data.copy_(b_s.data.to(b_t.data.dtype))

    return (lerp_params_,)


@app.cell
def _(config):
    def get_tau_jepa(step):
        """Linear ramp from τ_jepa_warmup → τ_jepa over `tau_jepa_warmup_steps`.

        This is the slow-start mitigation from the spec: a faster-tracking target
        encoder for the first few hundred steps lets the energy model find signal
        before the EMA rate slows back to the long-term value.
        """
        warmup_n = config["tau_jepa_warmup_steps"]
        if step >= warmup_n:
            return config["tau_jepa"]
        alpha = step / max(1, warmup_n)
        return (1.0 - alpha) * config["tau_jepa_warmup"] + alpha * config["tau_jepa"]

    return (get_tau_jepa,)


@app.cell
def _(
    accelerator,
    energy_model,
    lr_scheduler,
    optimizer,
    train_loader,
    val_loader,
):
    # accelerator.prepare wraps for device placement + bf16 autocast. The EMA
    # modules above are NOT prepared — they're plain fp32 modules on device.
    energy_model_p, optimizer_p, train_loader_p, val_loader_p, lr_scheduler_p = (
        accelerator.prepare(
            energy_model, optimizer, train_loader, val_loader, lr_scheduler
        )
    )
    return (
        energy_model_p,
        lr_scheduler_p,
        optimizer_p,
        train_loader_p,
        val_loader_p,
    )


@app.cell
def _(mo):
    mo.md(r"""
    ## Loss

    For each `(problem, clean_trace, corrupted_trace)` triple in a batch:

    1. `e_clean      = energy_model(problem, clean_trace)`     — online encodes problem, **JEPA target** encodes the clean trace.
    2. `e_corrupted  = energy_model(problem, corrupted_trace)` — online encodes problem, **JEPA target** encodes the corrupted trace.
    3. `loss = mean( relu(margin + e_clean − e_corrupted) )`

    Gradients flow into the **online encoder** and **fusion head** only; the JEPA
    target encoder is updated solely by the EMA step at the end of each iteration.
    """)
    return


@app.cell
def _(F):
    def margin_ranking_loss(e_clean, e_corrupted, margin):
        """L = mean( relu(m + E_clean − E_corrupted) )."""
        return F.relu(margin + e_clean - e_corrupted).mean()

    return (margin_ranking_loss,)


@app.cell
def _(torch):
    @torch.no_grad()
    def encoder_cosine_similarity(unwrapped_energy_model, fixed_problem_batch):
        """Mean cosine similarity between online and JEPA target encoder outputs
        on a fixed batch. Per spec, this is the collapse / divergence sanity:
            * stays at ~1.0 → encoders identical (collapsed); reduce τ_jepa.
            * drops to ~0.0 / oscillates → diverging; increase τ_jepa.
        Healthy training sits somewhere in between and slowly decreases as the
        online encoder specializes.
        """
        online = unwrapped_energy_model.online_encoder
        target = unwrapped_energy_model.target_encoder
        was_training_o, was_training_t = online.training, target.training
        online.eval()
        target.eval()
        try:
            e_o = online(fixed_problem_batch).flatten(1).float()
            e_t = target(fixed_problem_batch).flatten(1).float()
            return torch.nn.functional.cosine_similarity(e_o, e_t, dim=1).mean().item()
        finally:
            online.train(was_training_o)
            target.train(was_training_t)

    return (encoder_cosine_similarity,)


@app.cell
def _(margin_ranking_loss, torch):
    @torch.no_grad()
    def validate(model, loader, accelerator, margin):
        """Validation pass with whatever weights the model currently holds.

        Returns mean loss, margin satisfaction rate, and mean energy gap.
        Caller is responsible for swapping in EMA weights if EMA evaluation
        is desired (see the final EMA val cell).
        """
        model.eval()
        total_loss = 0.0
        total_n = 0
        total_satisfied = 0
        total_gap = 0.0
        for batch in loader:
            problem, clean_trace, corrupted_trace = batch
            with accelerator.autocast():
                e_clean = model(problem, clean_trace)
                e_corr = model(problem, corrupted_trace)
            loss = margin_ranking_loss(e_clean, e_corr, margin)
            n = problem.size(0)
            total_n += n
            total_loss += loss.item() * n
            # Margin satisfaction: fraction with E_clean + m < E_corrupted.
            total_satisfied += (e_clean + margin < e_corr).float().sum().item()
            total_gap += (e_corr - e_clean).float().sum().item()
        model.train()
        return {
            "loss": total_loss / max(1, total_n),
            "margin_satisfaction": total_satisfied / max(1, total_n),
            "energy_gap": total_gap / max(1, total_n),
        }

    return (validate,)


@app.cell
def _(accelerator, val_loader_p):
    # Stash a fixed val problem batch for the cosine-similarity sanity check.
    # Reusing the SAME batch across training keeps the signal stable enough
    # to interpret trends in the cosine number itself, not in the input.
    _it = iter(val_loader_p)
    _first_batch = next(_it)
    fixed_problem_batch = _first_batch[0].to(accelerator.device)
    del _it, _first_batch
    return (fixed_problem_batch,)


@app.cell
def _(accelerator, lerp_params_):
    def update_jepa_target_(model, tau):
        """JEPA target encoder EMA update (τ_jepa)."""
        unwrapped = accelerator.unwrap_model(model)
        lerp_params_(unwrapped.target_encoder, unwrapped.online_encoder, tau)

    return (update_jepa_target_,)


@app.cell
def _(accelerator, lerp_params_):
    def update_inference_ema_(model, ema_online, ema_fusion, tau):
        """Inference-time EMA update (τ_inf) on online encoder + fusion head."""
        unwrapped = accelerator.unwrap_model(model)
        lerp_params_(ema_online, unwrapped.online_encoder, tau)
        lerp_params_(ema_fusion, unwrapped.fusion_head, tau)

    return (update_inference_ema_,)


@app.function
def log_metrics(use_wandb, wandb, payload, step):
    if use_wandb:
        wandb.log(payload, step=step)
    else:
        head = f"[step {step}]"
        tail = " ".join(
            f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
            for k, v in payload.items()
        )
        print(f"{head} {tail}")


@app.cell
def _(
    accelerator,
    config,
    encoder_cosine_similarity,
    energy_model_p,
    fixed_problem_batch,
    get_tau_jepa,
    inference_ema_fusion_head,
    inference_ema_online_encoder,
    lr_scheduler_p,
    margin_ranking_loss,
    optimizer_p,
    train_loader_p,
    trainable_params,
    update_inference_ema_,
    update_jepa_target_,
    use_wandb,
    wandb,
):
    def train_one_epoch(epoch, global_step):
        energy_model_p.train()
        for batch in train_loader_p:
            problem, clean_trace, corrupted_trace = batch
            with accelerator.autocast():
                e_clean = energy_model_p(problem, clean_trace)
                e_corr = energy_model_p(problem, corrupted_trace)
                loss = margin_ranking_loss(e_clean, e_corr, config["margin"])

            accelerator.backward(loss)
            if (
                config["grad_clip_norm"] is not None
                and accelerator.sync_gradients
            ):
                accelerator.clip_grad_norm_(
                    trainable_params, config["grad_clip_norm"]
                )
            optimizer_p.step()
            lr_scheduler_p.step()
            optimizer_p.zero_grad(set_to_none=True)

            # ─── EMA updates (after each gradient step, per spec) ────────────
            tau_jepa_now = get_tau_jepa(global_step)
            update_jepa_target_(energy_model_p, tau_jepa_now)
            update_inference_ema_(
                energy_model_p,
                inference_ema_online_encoder,
                inference_ema_fusion_head,
                config["tau_inf"],
            )

            # ─── Step-level logging ──────────────────────────────────────────
            if (
                accelerator.is_main_process
                and global_step % config["log_every_steps"] == 0
            ):
                payload = {
                    "train/loss": loss.detach().float().item(),
                    "train/energy_gap_mean": (e_corr - e_clean).detach().float().mean().item(),
                    "train/e_clean_mean": e_clean.detach().float().mean().item(),
                    "train/e_corrupted_mean": e_corr.detach().float().mean().item(),
                    "train/lr": lr_scheduler_p.get_last_lr()[0],
                    "train/tau_jepa": tau_jepa_now,
                    "epoch": epoch,
                }
                log_metrics(use_wandb, wandb, payload, global_step)

            # Cosine-similarity collapse sanity (every N steps)
            if (
                accelerator.is_main_process
                and global_step > 0
                and global_step % config["cosine_check_every_steps"] == 0
            ):
                cos = encoder_cosine_similarity(
                    accelerator.unwrap_model(energy_model_p),
                    fixed_problem_batch,
                )
                log_metrics(
                    use_wandb,
                    wandb,
                    {"train/cosine_sim_online_target": cos},
                    global_step,
                )

            global_step += 1
        return global_step

    return (train_one_epoch,)


@app.cell
def _(
    accelerator,
    config,
    energy_model_p,
    train_one_epoch,
    use_wandb,
    val_loader_p,
    validate,
    wandb,
):
    # Outer training loop. End-of-epoch validation uses the LIVE (non-EMA)
    # weights — the inference EMA is evaluated separately at the end.
    global_step = 0
    epoch = -1
    val_metrics = None
    val_history = []
    for epoch in range(config["num_epochs"]):
        global_step = train_one_epoch(epoch, global_step)
        if accelerator.is_main_process:
            val_metrics = validate(
                energy_model_p, val_loader_p, accelerator, config["margin"]
            )
            payload = {f"val/{k}": v for k, v in val_metrics.items()}
            payload["epoch"] = epoch + 1
            log_metrics(use_wandb, wandb, payload, global_step)
            val_history.append({"epoch": epoch + 1, **val_metrics})
            print(
                f"[epoch {epoch + 1}/{config['num_epochs']}] "
                f"val_loss={val_metrics['loss']:.4f} "
                f"margin_sat={val_metrics['margin_satisfaction']:.3f} "
                f"gap={val_metrics['energy_gap']:.3f}"
            )
    return epoch, global_step


@app.cell
def _(
    accelerator,
    config,
    energy_model_p,
    inference_ema_fusion_head,
    inference_ema_online_encoder,
    torch,
    use_wandb,
    val_loader_p,
    validate,
    wandb,
):
    # Final EMA-weights validation: swap EMA → live, validate, swap back.
    # try/finally ensures the live weights are restored even if validate raises.
    @torch.no_grad()
    def _swap_in(ema_module, live_module):
        backup = {
            k: v.detach().clone() for k, v in live_module.state_dict().items()
        }
        live_module.load_state_dict(ema_module.state_dict())
        return backup

    ema_val_metrics = None
    if accelerator.is_main_process:
        _unwrapped = accelerator.unwrap_model(energy_model_p)
        _backup_online = None
        _backup_fusion = None
        try:
            _backup_online = _swap_in(
                inference_ema_online_encoder, _unwrapped.online_encoder
            )
            _backup_fusion = _swap_in(
                inference_ema_fusion_head, _unwrapped.fusion_head
            )
            ema_val_metrics = validate(
                energy_model_p, val_loader_p, accelerator, config["margin"]
            )
        finally:
            if _backup_online is not None:
                _unwrapped.online_encoder.load_state_dict(_backup_online)
            if _backup_fusion is not None:
                _unwrapped.fusion_head.load_state_dict(_backup_fusion)
        log_metrics(
            use_wandb,
            wandb,
            {f"val_ema/{k}": v for k, v in ema_val_metrics.items()},
            0,
        )
        print(f"[final EMA val] {ema_val_metrics}")
    return


@app.cell
def _(
    Path,
    accelerator,
    config,
    energy_model_p,
    epoch,
    global_step,
    inference_ema_fusion_head,
    inference_ema_online_encoder,
    lr_scheduler_p,
    np,
    optimizer_p,
    random,
    torch,
):
    # Save the stage 1 checkpoint with the schema from Project Conventions.
    if accelerator.is_main_process:
        _unwrapped = accelerator.unwrap_model(energy_model_p)
        ckpt_dir = Path(config["checkpoint_dir"])
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = ckpt_dir / config["checkpoint_filename"]

        rng_state = {
            "python": random.getstate(),
            "numpy": np.random.get_state(),
            "torch": torch.get_rng_state(),
            "cuda": (
                torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
            ),
        }

        checkpoint = {
            # Live (training) weights — keyed by component for stage 3/4 loaders.
            "model_state_dict": {
                "online_encoder": _unwrapped.online_encoder.state_dict(),
                "fusion_head": _unwrapped.fusion_head.state_dict(),
            },
            # Inference EMA — what the inference notebook will consume.
            "inference_ema_state_dict": {
                "online_encoder": inference_ema_online_encoder.state_dict(),
                "fusion_head": inference_ema_fusion_head.state_dict(),
            },
            # JEPA target encoder (separate, structural EMA).
            "jepa_target_encoder_state_dict": _unwrapped.target_encoder.state_dict(),
            # Optimizer / scheduler / bookkeeping.
            "optimizer_state_dict": optimizer_p.state_dict(),
            "scheduler_state_dict": lr_scheduler_p.state_dict(),
            "step": global_step,
            "epoch": epoch + 1,
            "rng_state": rng_state,
            "config": dict(config),
        }
        torch.save(checkpoint, ckpt_path)
        print(f"[stage 1] checkpoint saved → {ckpt_path}")
    return


@app.cell
def _(WANDB_AVAILABLE, accelerator, use_wandb, wandb):
    if WANDB_AVAILABLE and use_wandb and accelerator.is_main_process:
        wandb.finish()
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## What's saved

    `checkpoints/stage1_energy.pt` contains:

    - `model_state_dict["online_encoder" | "fusion_head"]` — **live** trained weights.
    - `inference_ema_state_dict["online_encoder" | "fusion_head"]` — EMA at τ_inf = 0.9999, **what the inference notebook loads**.
    - `jepa_target_encoder_state_dict` — JEPA target encoder weights (τ_jepa = 0.999).
    - `optimizer_state_dict`, `scheduler_state_dict`, `step`, `epoch`, `rng_state`, `config`.

    Stage 3 will reload all three weight dicts and continue training the energy
    model jointly with the diffusion model.

    ### Sanity expectations on a healthy run

    - Margin satisfaction climbs past 50% (random) within the first ~1–2 epochs and
      should reach **80%+** on easy-mix validation by convergence.
    - Mean energy gap `E_corrupted − E_clean` grows above the margin (1.0).
    - Cosine similarity between online and JEPA target encoder outputs sits
      somewhere in the **0.3–0.95** band — not pinned at 1.0 (collapse) and not
      at 0.0 (runaway divergence).
    """)
    return


if __name__ == "__main__":
    app.run()
