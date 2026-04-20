import marimo

__generated_with = "0.20.1"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Training
    """)
    return


@app.cell
def _():
    import os
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"

    import torch
    from torch import nn
    import torch.nn.functional as F
    from diffusers import DDPMPipeline, DDPMScheduler, UNet2DModel, VQModel
    from diffusers.optimization import get_cosine_schedule_with_warmup
    from datasets import load_dataset
    from accelerate import Accelerator
    from huggingface_hub import create_repo, upload_folder
    import torchvision.models as models
    from torchvision.transforms import Compose, ToTensor, Normalize, RandomHorizontalFlip
    from torch.utils.data import Dataset, DataLoader, random_split
    from pathlib import Path
    from torch.optim import AdamW
    from itertools import chain
    import lpips
    from torch_ema import ExponentialMovingAverage
    from torchvision import transforms
    from torchvision.transforms import functional as TF
    import gc
    from PIL import Image
    import matplotlib.pyplot as plt
    from IPython.display import clear_output, display
    import numpy as np
    from diffusers import DiffusionPipeline
    from tqdm import tqdm
    import sys


    torch.backends.cudnn.benchmark = True  # Optimizes CUDA kernels
    torch.set_float32_matmul_precision('high')  # For Ampere+ GPUs
    torch.backends.cuda.enable_flash_sdp(True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    return (
        Accelerator,
        AdamW,
        DDPMScheduler,
        DataLoader,
        Dataset,
        DiffusionPipeline,
        ExponentialMovingAverage,
        F,
        Image,
        Path,
        UNet2DModel,
        VQModel,
        chain,
        device,
        display,
        gc,
        get_cosine_schedule_with_warmup,
        models,
        nn,
        np,
        os,
        plt,
        random_split,
        torch,
        tqdm,
        transforms,
    )


@app.cell
def _():
    # Configuration
    class TrainingConfig:
        image_size = 512
        train_batch_size = 4
        eval_batch_size = 2
        sample_images = 1

        num_epochs = 1
        gradient_accumulation_steps = 1
        learning_rate = 5e-5
        lr_warmup_steps = 1000

        mixed_precision = "fp16"
        output_dir = "output"

        seed = 42
        save_image_epochs = 1
        save_model_epochs = 1
        validation_split = 0.05

    config = TrainingConfig()
    return (config,)


@app.cell
def _(Image, np, plt):
    def display_images_in_line(images, titles=None, figsize=(15, 5), cmap='gray'):
        num_images = len(images)
        (fig, axes) = plt.subplots(1, num_images, figsize=figsize)
        if num_images == 1:
            axes = [axes]
        for (_i, ax) in enumerate(axes):
            if isinstance(images[_i], Image.Image):
                img_array = images[_i]
            else:  # Handle both PIL Images and PyTorch tensors
                img_array = images[_i].cpu().numpy()
            ax.imshow(img_array, cmap=cmap)
            if titles and _i < len(titles):
                ax.set_title(titles[_i])
            ax.axis('off')
        plt.tight_layout()
        plt.show()

    def unnormalize(img_tensor):
        mean = 0.5
        std = 0.5
        img_tensor = img_tensor.squeeze()
        unnorm_img = img_tensor * std + mean
        return np.clip(unnorm_img, 0, 1)

    def unnormalize_to_PIL(img_tensor):
        mean = 0.5  # (H,W,1) -> (H,W)
        std = 0.5
        if len(img_tensor.shape) != 2:
            img_tensor = img_tensor.squeeze()
        unnorm_img = img_tensor * std + mean
        _img = np.clip(unnorm_img, 0, 1) * 255
        _img = _img.cpu().numpy().astype(np.uint8)
        return Image.fromarray(_img, 'L')

    def create_grid(images, rows=3, cols=3):
        tile_width = min((_img.width for _img in images))  # Ensure broadcasting works for (H,W,1) or (H,W)
        tile_height = min((_img.height for _img in images))
        resized_images = [_img.resize((tile_width, tile_height)) for _img in images]  # (H,W,1) -> (H,W)
        grid_width = tile_width * cols
        grid_height = tile_height * rows
        _grid = Image.new('RGB', (grid_width, grid_height))
        for (index, _img) in enumerate(resized_images):
            row = index // cols
            col = index % cols
            _grid.paste(_img, (col * tile_width, row * tile_height))
        return _grid  # Resize all images to common dimensions (using smallest width/height)  # Create blank canvas for grid  # Arrange images in grid pattern  # Which row (0-based)  # Which column (0-based)

    return create_grid, display_images_in_line, unnormalize, unnormalize_to_PIL


@app.cell
def _(Dataset, Image, Path):
    class PairedImageDataset(Dataset):

        def __init__(self, target_dir, transform=None):
            self.target_dir = Path(target_dir)
            self.files = sorted([f for f in self.target_dir.glob('*') if f.is_file()])
            self.transform = transform

        def __len__(self):
            return len(self.files)

        def __getitem__(self, idx):  # Load target image (grayscale 512)
            target_img = Image.open(self.files[_idx]).convert('L')
            if self.transform:
                target_img = self.transform(target_img)
            return (target_img, target_img)

        def set_transform(self, transform):
            self.transform = transform

    return (PairedImageDataset,)


@app.cell
def _(
    DataLoader,
    PairedImageDataset,
    config,
    display_images_in_line,
    random_split,
    torch,
    transforms,
    unnormalize,
):
    # Dataset preparation
    angiogram_path = '/app/code/diffusion-modeling/datasets/first_angio_frames'
    full_dataset = PairedImageDataset(angiogram_path, transform=None)
    val_size = int(len(full_dataset) * config.validation_split)
    # Create dataset with base transform
    train_size = len(full_dataset) - val_size  # Initialize without transform
    (train_dataset, val_dataset) = random_split(full_dataset, [train_size, val_size], generator=torch.Generator().manual_seed(config.seed))
    # Split into train and validation
    train_transform = transforms.Compose([transforms.RandomResizedCrop(config.image_size, scale=(0.5, 1.0), ratio=(0.8, 1.2)), transforms.RandomHorizontalFlip(), transforms.RandomVerticalFlip(), transforms.RandomRotation(90), transforms.RandomAffine(degrees=0, scale=(0.9, 1.1), shear=10), transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2), transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)), transforms.RandomPerspective(distortion_scale=0.2, p=0.5), transforms.ToTensor(), transforms.Normalize([0.5], [0.5])])
    val_transform = transforms.Compose([transforms.Resize((config.image_size, config.image_size)), transforms.ToTensor(), transforms.Normalize([0.5], [0.5])])
    train_dataset.dataset.set_transform(train_transform)
    val_dataset.dataset.set_transform(val_transform)
    train_dataloader = DataLoader(train_dataset, batch_size=config.train_batch_size, shuffle=True, num_workers=8)
    val_dataloader = DataLoader(val_dataset, batch_size=config.train_batch_size, shuffle=False, num_workers=8)
    val_batch = next(iter(val_dataloader))
    val_sample_image = val_batch[0][0]
    # Define transforms
    print(val_sample_image.shape)
    print(f'Train samples: {len(train_dataset)}, Validation samples: {len(val_dataset)}')
    print(f'Train batches: {len(train_dataloader)}, Validation batches: {len(val_dataloader)}')
    for (_i, _batch) in enumerate(val_dataloader):
        unnormal = []
        for _img in _batch:
            _sample = _img[0].permute(1, 2, 0)
            unnormal.append(unnormalize(_sample))
            _sample = _img[1].permute(1, 2, 0)  # Adds blur variation
            unnormal.append(unnormalize(_sample))  # Perspective shifts
        display_images_in_line(unnormal)
        if _i == 0:
    # Apply transforms to subsets
    # Create dataloaders AFTER setting transforms
            break  # Returns dictionary with "images" key  # Shape: [image_pairs, batch_size, channels, height, width]
    return train_dataloader, val_dataloader, val_sample_image


@app.cell
def _(VQModel, device, np):
    VQVAE = VQModel.from_pretrained("/app/code/diffusion-modeling/models/__synth_angio_pipeline__/VQ-VAE")
    VQVAE.to(device)

    latent_stats = np.load("/app/code/diffusion-modeling/models/__synth_angio_pipeline__/VQ-VAE/Latent_statistics.npy")
    latents_mean = latent_stats[0]
    latents_std = latent_stats[1]
    print(f"Avg Mean: {latents_mean}, Avg STD: {latents_std}")
    return (VQVAE,)


@app.cell
def _(VQVAE, device, np, torch, train_dataloader):
    try:
        latents = np.load('latent_stats.npy')
        mean = latents[0]
        std = latents[1]
        print(f'Mean: {mean}, STD: {std}')
    except:
        mean = []
        std = []
        for (_idx, _batch) in enumerate(train_dataloader):
            for _img in _batch:
                _sample = _img.to(device)
                with torch.no_grad():
                    _encoded = VQVAE.encode(_sample, return_dict=True).latents
                mean.append(_encoded.mean().item())
                std.append(_encoded.std().item())
            latents_mean_1 = np.array(mean).mean()
            latents_std_1 = np.array(std).mean()
            print(f'Idx: {_idx + 1}/{len(train_dataloader)}, Avg Mean: {latents_mean_1}, Avg STD: {latents_std_1}', end='\r')
        latents = np.array([np.array(mean).mean(), np.array(std).mean()])
        np.save('latent_stats.npy', latents)
    return latents_mean_1, latents_std_1


@app.cell
def _(
    Image,
    VQVAE,
    create_grid,
    device,
    display,
    latents_mean_1,
    latents_std_1,
    torch,
    unnormalize_to_PIL,
    val_sample_image,
):
    def encoder(image: torch.Tensor):
        with torch.no_grad():
            encoding = VQVAE.encode(image, return_dict=True).latents
            encoding = (encoding - latents_mean_1) / latents_std_1
        return encoding

    def decoder(latents: torch.Tensor):
        latents = latents * latents_std_1 + latents_mean_1
        with torch.no_grad():
            decoded = VQVAE.decode(latents, return_dict=True)
        return decoded.sample
    _img = val_sample_image.to(device)
    orig = unnormalize_to_PIL(_img.cpu().squeeze())
    _val_images = _img.unsqueeze(dim=1).to(device)
    _encoded = encoder(_val_images)
    print(f'Input shape: {_val_images.shape}')
    decoded = decoder(_encoded)
    recon = unnormalize_to_PIL(decoded.cpu().squeeze())
    encoded_image = unnormalize_to_PIL(_encoded.cpu().squeeze())
    encoded_image = encoded_image.resize((512, 512), resample=Image.LANCZOS)
    recon = recon.resize((512, 512), resample=Image.LANCZOS)
    comparison_images = [recon, encoded_image]
    latent_channels = _encoded.shape[1]
    latent_dim = _encoded.shape[2]
    latent_shape = _encoded.shape
    print(f'Latent shape: {latent_shape}, Latent channels: {latent_channels}, Latent dimensions: {latent_dim}')
    print(f'Latent mean: {_encoded.mean().item()}, Latent std: {_encoded.std().item()}')
    _grid = create_grid(comparison_images, rows=1, cols=len(comparison_images))
    display(_grid)
    return decoder, encoder, latent_channels, latent_dim


@app.cell
def _(
    Image,
    create_grid,
    display,
    models,
    nn,
    np,
    unnormalize,
    val_dataloader,
):
    # Sample image
    sample_batch = next(iter(val_dataloader))
    image_tensor = sample_batch[1]
    print(image_tensor.shape)
    _resnet = models.resnet50(pretrained=True)
    print(f'layer count {len(list(_resnet.children()))}')
    layers = -3
    _resnet = nn.Sequential(*list(_resnet.children())[:layers])
    features = _resnet(image_tensor.repeat(1, 3, 1, 1))
    print(features.shape)
    embedding_channels = features.shape[1]
    _img = features[0].detach().numpy()
    _feature_images = []
    for (_idx, _i) in enumerate(_img):
        _i = np.expand_dims(_i, 0)
        _i = unnormalize(_i.transpose(1, 2, 0))
        _feature_images.append(Image.fromarray((_i * 255).astype(np.uint8)).resize((256, 256)))
    _grid = create_grid(_feature_images, rows=3, cols=10)
    display(_grid)
    return embedding_channels, image_tensor, layers


@app.cell
def _(
    F,
    Image,
    create_grid,
    device,
    display,
    embedding_channels,
    encoder,
    image_tensor,
    latent_dim,
    layers,
    models,
    nn,
    np,
    torch,
    unnormalize,
):
    # Conditional Encoder (resnet)
    _resnet = models.resnet50(pretrained=True)
    _resnet = nn.Sequential(*list(_resnet.children())[:layers])

    class resnet_with_projector(nn.Module):
    # Combine into a sequential model

        def __init__(self, backbone):
            super().__init__()
            self.backbone = backbone
            for param in backbone.parameters():
                param.requires_grad = False
            half_embedding_channels = 2 ** (embedding_channels // 2).bit_length()
            self.adapter = nn.Sequential(nn.Conv2d(embedding_channels, half_embedding_channels, kernel_size=3, padding=1), nn.ReLU(), nn.Conv2d(half_embedding_channels, half_embedding_channels // 2 - 1, kernel_size=1))

        def forward(self, x):
            bs = x.shape[0]
            embedding = self.backbone(x)
            embedding = self.adapter(embedding)
            embedding = F.interpolate(embedding, size=(latent_dim, latent_dim), mode='bilinear', align_corners=False)
            return embedding
    conditional_encoder = resnet_with_projector(_resnet)
    conditional_encoder.to(device)
    with torch.no_grad():
        _embeddings = conditional_encoder(image_tensor.repeat(1, 3, 1, 1).to(device))
    print(f'final embeddings {_embeddings.shape}')
    _vqencoding = encoder(image_tensor.to(device))
    print(f'vq model {_vqencoding.shape}')
    _embeddings = torch.cat([_vqencoding, _embeddings], dim=1)
    model_input_channels = _embeddings.shape[1]
    print(f'input shape {_embeddings.shape}')
    _img = _embeddings[0].detach().cpu().numpy()
    _feature_images = []
    for (_idx, _i) in enumerate(_img):
        _i = np.expand_dims(_i, 0)
    # --------- TESTING CONDITIONAL ENCODER ---------
    # Extract embeddings
        _i = unnormalize(_i.transpose(1, 2, 0))
        _feature_images.append(Image.fromarray((_i * 255).astype(np.uint8)).resize((256, 256)))
    _grid = create_grid(_feature_images, rows=1, cols=4)
    display(_grid)
    return conditional_encoder, model_input_channels


@app.cell
def _(
    AdamW,
    DDPMScheduler,
    UNet2DModel,
    chain,
    conditional_encoder,
    config,
    get_cosine_schedule_with_warmup,
    latent_channels,
    latent_dim,
    model_input_channels,
    train_dataloader,
):
    # Suppose your noise is (batch, 1, H, W) and condition is (batch, 1024, H, W)
    model = UNet2DModel(
        sample_size=latent_dim,
        in_channels=model_input_channels,  # Noise + condition channels
        out_channels=latent_channels,
        block_out_channels=(320, 640, 1280, 2560),
        layers_per_block=2,
        down_block_types=("DownBlock2D",
                          "DownBlock2D",
                          "DownBlock2D",
                          "DownBlock2D"),
        up_block_types=("UpBlock2D",
                        "UpBlock2D",
                        "UpBlock2D",
                        "UpBlock2D"),
        norm_num_groups=32,
    )
    model.enable_xformers_memory_efficient_attention()

    noise_scheduler = DDPMScheduler(num_train_timesteps=1000)

    # Optimizer and LR scheduler
    optimizer = AdamW(
        chain(model.parameters(), conditional_encoder.adapter.parameters()),
        lr=config.learning_rate
    )

    lr_scheduler = get_cosine_schedule_with_warmup(
        optimizer=optimizer,
        num_warmup_steps=config.lr_warmup_steps,
        num_training_steps=len(train_dataloader) * config.num_epochs,
    )
    return lr_scheduler, model, noise_scheduler, optimizer


@app.cell
def _(
    DiffusionPipeline,
    conditional_encoder,
    latent_dim,
    torch,
    tqdm,
    unnormalize_to_PIL,
):
    class ConcatenatedPipeline(DiffusionPipeline):

        def __init__(self, unet, encoder, conditional_encoder, decoder, scheduler):
            super().__init__()
            self.unet = unet
            self.scheduler = scheduler
            self.encoder = encoder
            self.conditional_encoder = conditional_encoder
            self.decoder = decoder
            self.register_modules(unet=unet, scheduler=scheduler, encoder=encoder, decoder=decoder)

        def enable_xformers(self, attention_op=None):
            self.unet.enable_xformers_memory_efficient_attention(attention_op)
            return self

        @torch.no_grad()
        def __call__(self, condition_images, num_steps=1000, generator=None, guidance_scale=7.5, bar=False):
            device = next(self.unet.parameters()).device
            self.scheduler.set_timesteps(num_steps, device=device)
            if bar:  # Initialize progress bar
                diffusion_bar = tqdm(total=num_steps, desc='Diffusion Timesteps', leave=False)
            bs = condition_images.shape[0]
            condition_latents = conditional_encoder(condition_images.repeat(1, 3, 1, 1).to(device))
            latents = torch.randn((bs, 1, latent_dim, latent_dim), device=device, generator=generator)
            for t in self.scheduler.timesteps:
                noise_condition_latents = conditional_encoder(torch.randn_like(condition_images.repeat(1, 3, 1, 1).to(device)))  # Process condition images
                model_input_cond = torch.cat([latents, condition_latents], dim=1)
                cond_pred = self.unet(model_input_cond, t).sample
                model_input_uncond = torch.cat([latents, noise_condition_latents], dim=1)  # Initialize latents (noise)
                uncond_pred = self.unet(model_input_uncond, t).sample
                guided_pred = uncond_pred + guidance_scale * (cond_pred - uncond_pred)
                latents = self.scheduler.step(guided_pred, t, latents).prev_sample
                if bar:
                    diffusion_bar.update(1)
                    diffusion_bar.set_postfix({'Diffusion Steps': num_steps, 'Guidance Scale': guidance_scale})
            if bar:  # Diffusion process
                diffusion_bar.close()
            return self.latents_to_pil(latents)  # Random latents

        def latents_to_pil(self, latents):
            recon_list = []  # Conditional prediction
            images = self.decoder(latents)
            for _img in images:
                recon = unnormalize_to_PIL(_img.cpu().squeeze())
                recon_list.append(recon)  # Unconditional prediction
            return recon_list  # Classifier-free guidance interpolation  # Update latents  # Progress bar update

    return (ConcatenatedPipeline,)


@app.cell
def _(
    Image,
    device,
    encoder,
    latent_dim,
    np,
    torch,
    unnormalize_to_PIL,
    val_dataloader,
):
    def masked_mse_loss(imgs, prediction, target):
        loc = prediction.device
        total_loss = 0
        for (_img, preds, tar) in zip(imgs, prediction, target):
            orig = unnormalize_to_PIL(_img.cpu().squeeze())
            orig_ar = np.array(orig)
            mask = orig_ar == 0
            mask = torch.tensor(np.array(Image.fromarray(mask).resize((latent_dim, latent_dim)))).unsqueeze(dim=0).unsqueeze(dim=0)
            squared_error = (preds - tar) ** 2
            masked_error = torch.masked_select(squared_error.cpu(), mask)
            total_loss = total_loss + masked_error.sum() / (mask.sum() + 1e-08)
        return total_loss.to(loc)
    _img = next(iter(val_dataloader))[0]
    print(_img.shape)
    print()
    _val_images = _img.to(device)
    _encoded = encoder(_val_images)
    for _i in range(0, 1001, 250):
        noise_scale = _i / 1000
        noise = torch.randn_like(_encoded) * noise_scale
        loss = masked_mse_loss(_img, _encoded, _encoded + noise)
        print(f'Noise added: {noise_scale}, Loss: {loss}, Device: {loss.device}')
    return (masked_mse_loss,)


@app.cell
def _(
    Accelerator,
    ConcatenatedPipeline,
    ExponentialMovingAverage,
    F,
    Image,
    create_grid,
    device,
    display,
    gc,
    masked_mse_loss,
    np,
    os,
    torch,
    tqdm,
    unnormalize,
    unnormalize_to_PIL,
):
    def train_loop(config, model, encoder, conditional_encoder, decoder, noise_scheduler, optimizer, train_dataloader, val_dataloader, lr_scheduler):
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.set_float32_matmul_precision('high')
        accelerator = Accelerator(mixed_precision=config.mixed_precision, project_dir=os.path.join(config.output_dir, 'logs'), gradient_accumulation_steps=config.gradient_accumulation_steps)
        (model, encoder, decoder, optimizer, train_dataloader, val_dataloader, lr_scheduler) = accelerator.prepare(model, encoder, decoder, optimizer, train_dataloader, val_dataloader, lr_scheduler)
        model.enable_xformers_memory_efficient_attention()
        ema = ExponentialMovingAverage(list(model.parameters()) + list(conditional_encoder.adapter.parameters()), decay=0.9999)
        ema = accelerator.prepare(ema)
        global_step = 0
        loss_logging = []
        for epoch in range(config.num_epochs):
            model.train()
            total_train_mse_loss = 0
            total_train_border_loss = 0
            progress_bar = tqdm(total=len(train_dataloader), desc=f'Epoch {epoch + 1}')
            for (step, _batch) in enumerate(train_dataloader):
                (clean_images, condition_images) = _batch
                condition_latents = conditional_encoder(condition_images.repeat(1, 3, 1, 1).to(device))
                clean_latents = encoder(clean_images.to(accelerator.device))
                noise = torch.randn(clean_latents.shape, device=clean_images.device)
                bs = clean_latents.shape[0]
                timesteps = torch.randint(0, noise_scheduler.config.num_train_timesteps, (bs,), device=clean_latents.device).long()
                noisy_latents = noise_scheduler.add_noise(clean_latents, noise, timesteps)
                cond_drop_prob = 0.25
                if torch.rand(1).item() < cond_drop_prob:
                    condition_latents = conditional_encoder(torch.randn_like(condition_images.repeat(1, 3, 1, 1).to(device)))
                    dropped = 'Noise'
                else:
                    dropped = 'Condition'
                with accelerator.accumulate(model):
                    model_input = torch.cat([noisy_latents, condition_latents], dim=1)
                    noise_pred = model(model_input, timesteps).sample
                    mse_loss = F.mse_loss(noise_pred, noise)
                    border_loss = masked_mse_loss(clean_images, noise_pred, noise)
                    loss = mse_loss * 1 + border_loss * 0.1
                    total_train_mse_loss = total_train_mse_loss + mse_loss.detach().item()
                    total_train_border_loss = total_train_border_loss + border_loss.detach().item()
                    accelerator.backward(loss)
                    if accelerator.sync_gradients:
                        accelerator.clip_grad_norm_(model.parameters(), 1.0)
                    optimizer.step()
                    ema.update()
                    lr_scheduler.step()
                    optimizer.zero_grad()
                progress_bar.update(1)
                logs = {'mse_loss': total_train_mse_loss / (step + 1), 'border_loss': total_train_border_loss / (step + 1), 'training_on': dropped, 'lr': lr_scheduler.get_last_lr()[0]}
                progress_bar.set_postfix(**logs)
                accelerator.log(logs, step=global_step)
                global_step = global_step + 1
            progress_bar.close()
            gc.collect()
            torch.cuda.empty_cache()
            if accelerator.is_main_process and ((epoch + 1) % config.save_image_epochs == 0 or epoch + 1 == config.num_epochs):
                with ema.average_parameters():
                    model.eval()
                    with torch.no_grad():
                        pipeline = ConcatenatedPipeline(model, encoder, conditional_encoder, decoder, noise_scheduler)
                        generator = torch.Generator(device=accelerator.device)
                        samples = []
                        progress_bar = tqdm(total=config.eval_batch_size * config.sample_images, desc=f'Validation Samples')
                        loader = iter(val_dataloader)
                        for _i in range(config.eval_batch_size):
                            sample_batch = next(loader)
                            condition_img = sample_batch[1][_i].unsqueeze(0)
                            if _i % 2 == 1:
                                condition_img = torch.randn_like(condition_img)
                            condition = condition_img.repeat(config.sample_images, 1, 1, 1)
                            outputs = pipeline(condition_images=condition.to(accelerator.device), num_steps=1000, generator=generator, bar=False)
                            condition_img = unnormalize_to_PIL(condition_img.cpu())
                            output_imgs = []
                            for output in outputs[:config.sample_images]:
                                if isinstance(output, torch.Tensor):
                                    _img = output.squeeze().cpu().numpy()
                                    _img = unnormalize(_img.transpose(1, 2, 0))
                                    output_imgs.append(Image.fromarray((_img * 255).astype(np.uint8)))
                                else:
                                    output_imgs.append(output)
                            imgs = [condition_img] + output_imgs
                            samples.extend(imgs)
                            progress_bar.update(config.sample_images)
                        progress_bar.close()
                        pipeline.unet.save_pretrained(config.output_dir + '/unet')
                        pipeline.scheduler.save_pretrained(config.output_dir + '/scheduler')
                        torch.save(conditional_encoder.adapter.state_dict(), 'adapter_ema.pth')
                        loss_logging.append(loss.cpu().item())
                        np.save(f'{config.output_dir}/history.npy', np.array(loss_logging))
                _grid = create_grid(samples[0:2 * (config.sample_images + 1)], rows=2, cols=config.sample_images + 1)
                display(_grid)
                _grid = create_grid(samples, rows=config.eval_batch_size, cols=config.sample_images + 1)
                _grid.save(f'/app/code/diffusion-modeling/models/__synth_angio_pipeline__/conditional_background_generation/output/logs/epoch_{epoch + 1}_sample.jpg')

    return (train_loop,)


@app.cell
def _(
    conditional_encoder,
    config,
    decoder,
    encoder,
    lr_scheduler,
    model,
    noise_scheduler,
    optimizer,
    train_dataloader,
    train_loop,
    val_dataloader,
):
    # Launch training
    from accelerate import notebook_launcher


    args = (config, model, encoder, conditional_encoder, decoder, noise_scheduler, optimizer, 
            train_dataloader, val_dataloader, lr_scheduler)

    notebook_launcher(train_loop, args, num_processes=1)
    return


@app.cell
def _(config, np, plt):
    losses = np.load(f"{config.output_dir}/history.npy")

    plt.plot(np.arange(1, len(losses) + 1), losses, marker='o')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.title('Training Loss by Epoch')
    plt.grid(True)
    plt.show()
    return


@app.cell
def _(
    Image,
    conditional_encoder,
    create_grid,
    device,
    display,
    encoder,
    image_tensor,
    np,
    torch,
    unnormalize,
):
    with torch.no_grad():
        _embeddings = conditional_encoder(image_tensor.repeat(1, 3, 1, 1).to(device))
    print(f'final embeddings {_embeddings.shape}')
    _vqencoding = encoder(image_tensor.to(device))
    print(f'vq model {_vqencoding.shape}')
    _embeddings = torch.cat([_vqencoding, _embeddings], dim=1)
    model_input_channels_1 = _embeddings.shape[1]
    print(f'input shape {_embeddings.shape}')
    _img = _embeddings[0].detach().cpu().numpy()
    _feature_images = []
    for (_idx, _i) in enumerate(_img):
        _i = np.expand_dims(_i, 0)
        _i = unnormalize(_i.transpose(1, 2, 0))
        _feature_images.append(Image.fromarray((_i * 255).astype(np.uint8)).resize((256, 256)))
    _grid = create_grid(_feature_images, rows=1, cols=4)
    display(_grid)
    return


if __name__ == "__main__":
    app.run()
