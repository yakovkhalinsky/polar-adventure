# Polar Adventures Asset Pipeline

This folder contains the ComfyUI-driven asset generation pipeline for *Polar Adventures*.

## Quick start

1. Make sure ComfyUI is running at `http://note:8188`.
2. From the project root run:

```bash
python3 .comfyui-workflows/generate_polar_assets_v2.py --mode turbo
python3 .comfyui-workflows/postprocess_assets.py
npm run build
```

## Windows ComfyUI Desktop setup

Run one of these PowerShell scripts **on your Windows PC** to install the recommended model stack:

### Standard script (works in Windows PowerShell 5.1 / PowerShell 7)

```powershell
.\setup_windows_comfyui.ps1
```

### Fast script (requires PowerShell 7.2+ for parallel downloads)

```powershell
.\setup_windows_comfyui_fast.ps1
```

The fast version downloads multiple models in parallel, resumes interrupted transfers, and updates existing custom nodes.

Both scripts default to the ComfyUI Desktop install path:

```text
C:\Users\yakov\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI
```

If your install is elsewhere, pass the path:

```powershell
.\setup_windows_comfyui.ps1 -ComfyUiPath "C:\Path\To\Your\ComfyUI"
```

It downloads:

- SD 1.5 base checkpoint (`v1-5-pruned-emaonly.safetensors`)
- Improved VAE
- ControlNet OpenPose + Canny

It also installs the custom nodes:

- `ComfyUI-layerdiffuse`
- `rembg-comfyui-node`
- `ComfyUI-AdvancedTiling`

You will still need to download LoRAs manually from Civitai because they require login.

## Modes

### `--mode turbo` (default)

Uses the existing **z-image-turbo** AuraFlow setup:

- `z_image_turbo_bf16.safetensors` (UNet)
- `qwen_3_4b.safetensors` (CLIP)
- `ae.safetensors` (VAE)

This is the heaviest option. On an RTX 4060 8GB it works but leaves little headroom.

### `--mode sd15` (recommended for 8GB)

Uses a smaller **Stable Diffusion 1.5** checkpoint, leaving room for LoRAs,
ControlNet, and transparent-background nodes.

Required models after running the setup script:

- Checkpoint: `v1-5-pruned-emaonly.safetensors` in `ComfyUI/models/checkpoints/`
- VAE: `vae-ft-mse-840000-ema-pruned.safetensors` in `ComfyUI/models/vae/`

Optional upgrades for much better results:

- LoRA: isometric or pixel-art style LoRA in `ComfyUI/models/loras/`
- ControlNet: `control_v11p_sd15_openpose.pth` for consistent polar-bear poses
- Nodes: `ComfyUI-layerdiffuse` for native transparent PNG output

## Manual ComfyUI workflow JSONs

If you prefer to work directly in the ComfyUI Desktop app, import one of these workflows:

| File | Purpose |
|------|---------|
| `polar_bear_single_sd15.json` | Single-frame SD 1.5 polar bear for testing your model stack. |
| `polar_bear_single_turbo.json` | Single-frame z-image-turbo polar bear if you want to keep the AuraFlow stack. |
| `polar_bear_walk_v1.json` | Older single-frame test workflow. |
| `polar_bear_walk_16frame.json` | Template for a full 16-frame walk cycle. |

The SD 1.5 single-frame workflow expects only `v1-5-pruned-emaonly.safetensors`.
The 16-frame and v1 workflows work best with an isometric/pixel-art LoRA loaded.

## What gets generated

Source images land in `assets-src/`:

- `polar_bear_{north,east,south,west}_00001_.png`
- `tile_{snow,ice,ice_cracks}_00001_.png`

Post-processing converts them into game-ready files in `public/assets/`:

- `public/assets/characters/polar-bear.png` — 256×256 spritesheet (4 directions × 4 frames)
- `public/assets/tiles/{snow,ice,ice-cracks}.png` — 64×32 diamond isometric tiles

## How the transparency works

The v2 workflow prompts for a **bright lime green** background (`#00ff00`).
`postprocess_assets.py` samples the corners of each source image to detect that
background color and keys it out, leaving the foreground at full opacity. The tile
images then get masked to a 64×32 isometric diamond.

## Troubleshooting

### Tiles look empty or semi-transparent

- Check that the generated source images actually have a uniform background.
- If the AI ignored the lime-green prompt, open `postprocess_assets.py` and tune
  the `tolerance=` value in `remove_background()`.

### Site shows empty squares on GitHub Pages

The game loads assets with **relative** paths (`assets/...`). If you deploy to a
custom domain sub-path like `/polar-adventure/`, make sure `vite.config.ts` has
`base: './'` and the game code uses `assets/...`, not `/assets/...`.

## Asset manifest

`public/assets/manifest.json` is generated automatically and documents the frame
layout for the polar bear spritesheet and the tile filenames.
