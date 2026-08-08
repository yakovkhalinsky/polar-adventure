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

Run this PowerShell script **on your Windows PC** to install the recommended model stack:

```powershell
.\setup_windows_comfyui.ps1
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
| `polar_bear_walk_v1.json` | Single polar bear front-view frame. Good for testing your model stack. |
| `polar_bear_walk_16frame.json` | Template for a full 16-frame walk cycle. Duplicate the prompt/sampler/save chain for each direction and pose. |

Both workflows expect:

- `v1-5-pruned-emaonly.safetensors`
- An isometric/pixel-art LoRA (edit the `LoraLoader` widget to match your filename)

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
