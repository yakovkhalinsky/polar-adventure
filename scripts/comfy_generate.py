#!/usr/bin/env python3
"""Queue ComfyUI prompts and assemble real game assets.

This script generates into public/assets/generated/ for review, then optionally
promotes them into the active asset folders. It produces one object at a time
with very strict prompts, and assembles the polar bear spritesheet from
individual direction frames.

Usage:
    python3 scripts/comfy_generate.py --server http://note:8188 --preview-all
    python3 scripts/comfy_generate.py --server http://note:8188 --promote
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public/assets"
PREVIEW = OUT / "generated"


VOXEL_LORA = "VoxelXL_v1.safetensors"
VOXEL_LORA_WEIGHT = 0.85


def apply_lora(positive: str) -> str:
    """Append the Voxel XL LoRA tag to a prompt when LoRA is enabled."""
    if VOXEL_LORA is None:
        return positive
    return f"{positive}, <lora:{VOXEL_LORA}:{VOXEL_LORA_WEIGHT}>"


def list_models(server: str, model_type: str) -> list[str]:
    """Return the list of installed model files of a given type."""
    url = urljoin(server, f"/api/models/{model_type}")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def require_lora(server: str) -> None:
    """Exit with a helpful message if the Voxel XL LoRA is not yet loaded."""
    if VOXEL_LORA is None:
        return
    available = list_models(server, "loras")
    if VOXEL_LORA not in available:
        print(f"ERROR: {VOXEL_LORA} is not loaded by ComfyUI.", file=sys.stderr)
        print("       Run the setup script, then restart ComfyUI Desktop completely.", file=sys.stderr)
        print("       After restart, verify the LoRA appears in the model list.", file=sys.stderr)
        sys.exit(1)


def base_workflow(width: int, height: int, positive: str, negative: str, seed: int,
                  checkpoint: str = "cartoonxl_v10.safetensors", steps: int = 35, cfg: float = 7.5,
                  lora_name: str | None = None, lora_weight: float | None = None) -> dict[str, Any]:
    """SDXL txt2img workflow with optional LoRA."""
    if lora_name is None:
        lora_name = VOXEL_LORA
    if lora_weight is None:
        lora_weight = VOXEL_LORA_WEIGHT
    model_loader = "1"
    # If LoRA is specified, insert a LoraLoaderModelOnly node between checkpoint and sampler.
    if lora_name:
        return {
            "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
            "10": {
                "class_type": "LoraLoaderModelOnly",
                "inputs": {
                    "model": ["1", 0],
                    "lora_name": lora_name,
                    "strength_model": lora_weight,
                },
            },
            "2": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["1", 1]}},
            "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
            "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["10", 0],
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "positive": ["2", 0],
                    "negative": ["3", 0],
                    "latent_image": ["4", 0],
                    "denoise": 1.0,
                },
            },
            "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
            "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "polar_adv", "images": ["6", 0]}},
        }

    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": [model_loader, 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["4", 0],
                "denoise": 1.0,
            },
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "polar_adv", "images": ["6", 0]}},
    }


def img2img_workflow(width: int, height: int, positive: str, negative: str, seed: int,
                     image_path: Path, denoise: float = 0.55,
                     checkpoint: str = "cartoonxl_v10.safetensors", steps: int = 30, cfg: float = 7.0,
                     lora_name: str | None = None, lora_weight: float | None = None) -> dict[str, Any]:
    """Img2img workflow with optional LoRA."""
    if lora_name is None:
        lora_name = VOXEL_LORA
    if lora_weight is None:
        lora_weight = VOXEL_LORA_WEIGHT
    model_loader = "10" if lora_name else "1"
    workflow: dict[str, Any] = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["1", 1]}},
        "8": {"class_type": "LoadImage", "inputs": {"image": str(image_path)}},
        "9": {"class_type": "VAEEncode", "inputs": {"pixels": ["8", 0], "vae": ["1", 2]}},
        "5": {
            "class_type": "KSampler",
            "inputs": {
                "model": [model_loader, 0],
                "seed": seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "positive": ["2", 0],
                "negative": ["3", 0],
                "latent_image": ["9", 0],
                "denoise": denoise,
            },
        },
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "polar_adv", "images": ["6", 0]}},
    }
    if lora_name:
        workflow["10"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": lora_name,
                "strength_model": lora_weight,
            },
        }
        workflow["5"]["inputs"]["model"] = ["10", 0]
    return workflow


NEGATIVE_SPRITE = (
    "blurry, low quality, deformed, extra limbs, bad anatomy, watermark, signature, "
    "text, letters, words, cropped, out of frame, worst quality, collage, multiple objects, "
    "scene, landscape, background elements, border, frame, shadow, realistic, photograph, "
    "duplicated, repeated pattern, many items, scattered, icon set, sprite sheet, atlas, "
    "depth of field, gradient background, noisy background"
)

NEGATIVE_SHEET = NEGATIVE_SPRITE + ", inconsistent character, different poses per frame"

STYLE_PREFIX = "voxel style, low poly, Fez-like, blocky 3D, isometric, cute, "
SINGLE_OBJECT = (
    f"{STYLE_PREFIX}one single centered game asset taking up most of the canvas, "
    "pure white background, large empty white margin around it, "
    "no text, no watermark, no border, no frame, isolated object"
)

ASSETS: dict[str, dict[str, Any]] = {
    "rock": {
        "prompt": f"{SINGLE_OBJECT}, grey arctic rock boulder, rough surface, small snow patches",
        "size": 128,
        "out": PREVIEW / "objects/rock.png",
    },
    "iceberg": {
        "prompt": f"{SINGLE_OBJECT}, tall blue ice crystal chunk, translucent ice, white highlights",
        "size": 128,
        "out": PREVIEW / "objects/iceberg.png",
    },
    "tree": {
        "prompt": f"{SINGLE_OBJECT}, snow covered pine tree, green needles, white snow cap",
        "size": 128,
        "out": PREVIEW / "objects/tree.png",
    },
    "snow-mound": {
        "prompt": f"{SINGLE_OBJECT}, small mound of snow, smooth white surface, soft shadows",
        "size": 128,
        "out": PREVIEW / "objects/snow-mound.png",
    },
    "igloo": {
        "prompt": f"{SINGLE_OBJECT}, isometric igloo dome, white ice blocks, small brown entrance",
        "size": 128,
        "out": PREVIEW / "objects/igloo.png",
    },
    "sign": {
        "prompt": f"{SINGLE_OBJECT}, wooden signpost with blank board and snow on top, no text",
        "size": 128,
        "out": PREVIEW / "objects/sign.png",
    },
    "fish": {
        "prompt": f"{SINGLE_OBJECT}, frozen arctic fish, red and silver scales, side view",
        "size": 128,
        "out": PREVIEW / "objects/fish.png",
    },
    "penguin": {
        "prompt": f"{SINGLE_OBJECT}, cute cartoon penguin standing upright, black and white body, orange beak and feet",
        "size": 128,
        "out": PREVIEW / "characters/penguin.png",
    },
}


def submit(server: str, workflow: dict[str, Any]) -> str:
    url = urljoin(server, "/prompt")
    resp = requests.post(
        url,
        json={"prompt": workflow, "client_id": "polar-adventures-cli"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def poll_until_done(server: str, prompt_id: str, timeout: float = 300.0) -> dict[str, Any]:
    url = urljoin(server, f"/history/{prompt_id}")
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if prompt_id in data:
            entry = data[prompt_id]
            if entry.get("status", {}).get("status_str") == "success":
                return entry
            if entry.get("status", {}).get("completed"):
                return entry
        time.sleep(2.0)
    raise RuntimeError(f"Prompt {prompt_id} did not complete within {timeout}s")


def download_image(server: str, filename: str, subfolder: str, dest: Path) -> None:
    url = urljoin(server, "/view")
    resp = requests.get(
        url,
        params={"filename": filename, "subfolder": subfolder, "type": "output"},
        timeout=60,
    )
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    print(f"  downloaded {dest}")


def isolate_largest_sprite(img: Image.Image, target_size: int, bg_threshold: int = 30) -> Image.Image:
    """Crop to the largest foreground region and make the dominant background transparent.

    Works for white, grey, blue, or any near-solid background by comparing each pixel
    to the average corner color.
    """
    rgba = img.convert("RGBA")
    width, height = rgba.size

    # Sample the four corners to estimate the background color.
    corners = [
        rgba.getpixel((2, 2)),
        rgba.getpixel((width - 3, 2)),
        rgba.getpixel((2, height - 3)),
        rgba.getpixel((width - 3, height - 3)),
    ]
    bg_r = sum(c[0] for c in corners) // 4
    bg_g = sum(c[1] for c in corners) // 4
    bg_b = sum(c[2] for c in corners) // 4

    # Build a transparency mask: pixels close to the corner color become transparent.
    pixels = list(rgba.getdata())
    new_pixels = []
    for r, g, b, a in pixels:
        dist = abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b)
        if dist < bg_threshold:
            new_pixels.append((255, 255, 255, 0))
        else:
            # Slightly feather near-background pixels for smoother edges.
            alpha = a if dist > bg_threshold * 2 else int(a * dist / (bg_threshold * 2))
            new_pixels.append((r, g, b, alpha))
    rgba.putdata(new_pixels)

    # Crop to the non-transparent bounding box.
    alpha = rgba.split()[-1]
    bbox = alpha.getbbox()
    if bbox:
        crop = rgba.crop(bbox)
    else:
        crop = rgba

    # Scale to fit inside target with padding.
    scale = target_size / max(crop.size) * 0.85
    new_size = (max(1, int(crop.width * scale)), max(1, int(crop.height * scale)))
    crop = crop.resize(new_size, Image.Resampling.LANCZOS)

    out = Image.new("RGBA", (target_size, target_size), (255, 255, 255, 0))
    x = (target_size - crop.width) // 2
    y = (target_size - crop.height) // 2
    out.paste(crop, (x, y), crop)
    return out


def generate_single(server: str, key: str, seed: int, use_img2img: bool = False,
                    guide: Path | None = None) -> Path:
    spec = ASSETS[key]
    size = spec["size"]
    prompt = apply_lora(spec["prompt"])

    # SDXL works best at native resolution; scale up and isolate/downscale.
    gen_size = 1024

    if use_img2img and guide and guide.exists():
        workflow = img2img_workflow(gen_size, gen_size, prompt, NEGATIVE_SPRITE, seed, guide, denoise=0.55)
    else:
        workflow = base_workflow(gen_size, gen_size, prompt, NEGATIVE_SPRITE, seed)

    prompt_id = submit(server, workflow)
    print(f"[{key}] queued {prompt_id}")
    entry = poll_until_done(server, prompt_id)
    images = entry.get("outputs", {}).get("7", {}).get("images", [])
    if not images:
        raise RuntimeError(f"No images returned for {key}")

    download_image(server, images[0]["filename"], images[0].get("subfolder", ""), spec["out"])

    with Image.open(spec["out"]).convert("RGBA") as img:
        isolated = isolate_largest_sprite(img, size)
        isolated.save(spec["out"])
        print(f"  isolated -> {size}x{size}")

    return spec["out"]


def make_bear_reference(server: str, seed: int) -> Path:
    """Generate a single consistent voxel polar bear reference on white."""
    prompt = apply_lora(
        f"{STYLE_PREFIX}single cute polar bear character design, standing facing forward, "
        "small black eyes, rounded ears, white fur, full body visible, "
        "centered on pure white background, no text, no watermark, no border, no shadow"
    )
    out = PREVIEW / "characters/bear-reference.png"
    workflow = base_workflow(1024, 1024, prompt, NEGATIVE_SPRITE, seed)
    prompt_id = submit(server, workflow)
    print(f"[bear-reference] queued {prompt_id}")
    entry = poll_until_done(server, prompt_id)
    images = entry.get("outputs", {}).get("7", {}).get("images", [])
    download_image(server, images[0]["filename"], images[0].get("subfolder", ""), out)
    with Image.open(out).convert("RGBA") as img:
        isolate_largest_sprite(img, 512).save(out)
    return out


def make_bear_direction(server: str, direction: str, reference: Path, seed: int) -> Path:
    """Generate one direction frame using the reference color/style in prompt."""
    directions = {
        "up": "seen from behind, walking away, back view, facing away",
        "right": "side view walking to the right, facing right",
        "down": "front view walking toward viewer, facing camera",
        "left": "side view walking to the left, facing left",
    }
    prompt = apply_lora(
        f"{STYLE_PREFIX}single cute polar bear character, same voxel design as reference, "
        f"{directions[direction]}, "
        "small black eyes, rounded ears, white fur, full body visible, "
        "centered on pure white background, no text, no watermark, no border, no shadow"
    )
    out = PREVIEW / f"characters/bear-{direction}.png"
    workflow = base_workflow(1024, 1024, prompt, NEGATIVE_SPRITE, seed)
    prompt_id = submit(server, workflow)
    print(f"[bear-{direction}] queued {prompt_id}")
    entry = poll_until_done(server, prompt_id)
    images = entry.get("outputs", {}).get("7", {}).get("images", [])
    download_image(server, images[0]["filename"], images[0].get("subfolder", ""), out)

    with Image.open(out).convert("RGBA") as img:
        isolate_largest_sprite(img, 512).save(out)
        print(f"  isolated bear-{direction}")

    return out


def assemble_bear_sheet(directions: dict[str, Path]) -> Path:
    """Assemble 4 directions x 8 rows into a 512x1024 spritesheet.

    Rows: walk-up, walk-right, walk-down, walk-left, swim, attack, push, idle.
    For now each row repeats the same direction frame 4 times.
    """
    cell = 128
    sheet = Image.new("RGBA", (cell * 4, cell * 8), (255, 255, 255, 255))

    order = ["up", "right", "down", "left"]
    frames: dict[str, Image.Image] = {}
    for d in order:
        img = Image.open(directions[d]).convert("RGBA")
        # Scale/crop to cell, keeping centered.
        scale = cell / max(img.size)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        frame = Image.new("RGBA", (cell, cell), (255, 255, 255, 0))
        x = (cell - img.width) // 2
        y = (cell - img.height) // 2
        frame.paste(img, (x, y), img)
        frames[d] = frame

    # Row mapping for walk directions.
    row_dirs = ["up", "right", "down", "left", "down", "down", "down", "down"]
    for row, d in enumerate(row_dirs):
        for col in range(4):
            sheet.paste(frames[d], (col * cell, row * cell), frames[d])

    out = PREVIEW / "characters/polar-bear.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"  assembled {out}")
    return out


def make_tile_atlas(server: str, seed: int) -> Path:
    """Generate four individual 64x32 voxel isometric tiles and pack them."""
    tiles = [
        ("snow", "smooth white snow isometric diamond tile, soft shadows, white and pale blue"),
        ("ice", "light blue ice isometric diamond tile, glossy frozen surface"),
        ("ice-cracks", "cracked ice isometric diamond tile, dark cracks in light blue ice"),
        ("water", "deep blue water isometric diamond tile, small wave highlights"),
    ]

    atlas = Image.new("RGBA", (256, 64), (255, 255, 255, 255))
    for i, (name, desc) in enumerate(tiles):
        prompt = apply_lora(
            f"{STYLE_PREFIX}single isometric game tile, {desc}, "
            "pure white background, centered diamond shape, no text, no border, no frame"
        )
        workflow = base_workflow(1024, 1024, prompt, NEGATIVE_SPRITE, seed + i)
        prompt_id = submit(server, workflow)
        print(f"[tile-{name}] queued {prompt_id}")
        entry = poll_until_done(server, prompt_id)
        images = entry.get("outputs", {}).get("7", {}).get("images", [])
        tmp = PREVIEW / f"tiles/{name}-raw.png"
        download_image(server, images[0]["filename"], images[0].get("subfolder", ""), tmp)
        with Image.open(tmp).convert("RGBA") as img:
            isolated = isolate_largest_sprite(img, 64)
            # Stretch isolated sprite into a 64x32 diamond.
            diamond = isolated.resize((64, 32), Image.Resampling.LANCZOS)
            diamond.save(PREVIEW / f"tiles/{name}.png")
        tile = Image.open(PREVIEW / f"tiles/{name}.png").convert("RGBA")
        atlas.paste(tile, (i * 64, 0), tile)

    out = PREVIEW / "tiles/tile-atlas.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    atlas.save(out)
    print(f"  assembled {out}")
    return out


def promote() -> None:
    """Copy preview assets into the active asset folders."""
    mappings = [
        (PREVIEW / "characters/polar-bear.png", OUT / "characters/polar-bear.png"),
        (PREVIEW / "characters/penguin.png", OUT / "characters/penguin.png"),
        (PREVIEW / "objects/rock.png", OUT / "objects/rock.png"),
        (PREVIEW / "objects/iceberg.png", OUT / "objects/iceberg.png"),
        (PREVIEW / "objects/tree.png", OUT / "objects/tree.png"),
        (PREVIEW / "objects/snow-mound.png", OUT / "objects/snow-mound.png"),
        (PREVIEW / "objects/fish.png", OUT / "objects/fish.png"),
        (PREVIEW / "objects/igloo.png", OUT / "objects/igloo.png"),
        (PREVIEW / "objects/sign.png", OUT / "objects/sign.png"),
        (PREVIEW / "tiles/snow.png", OUT / "tiles/snow.png"),
        (PREVIEW / "tiles/ice.png", OUT / "tiles/ice.png"),
        (PREVIEW / "tiles/ice-cracks.png", OUT / "tiles/ice-cracks.png"),
        (PREVIEW / "tiles/water.png", OUT / "tiles/water.png"),
    ]
    for src, dst in mappings:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.replace(dst)
            print(f"promoted {src} -> {dst}")
        else:
            print(f"skip {src} (not generated yet)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate real game assets via ComfyUI")
    parser.add_argument("--server", default="http://note:8188")
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--preview", choices=list(ASSETS.keys()), help="Generate one preview asset")
    parser.add_argument("--preview-all", action="store_true", help="Generate all single preview assets")
    parser.add_argument("--preview-bear", action="store_true", help="Generate polar bear reference + directions + sheet")
    parser.add_argument("--preview-tiles", action="store_true", help="Generate tile atlas")
    parser.add_argument("--promote", action="store_true", help="Copy previews to active asset folders")
    parser.add_argument("--no-lora", action="store_true", help="Use CartoonXL without the Voxel XL LoRA (not voxel style)")
    args = parser.parse_args()

    if args.no_lora:
        global VOXEL_LORA
        VOXEL_LORA = None

    if args.promote:
        promote()
        return

    if not args.no_lora:
        require_lora(args.server)

    jobs: list[str] = []
    if args.preview_all:
        jobs.extend(ASSETS.keys())
    elif args.preview:
        jobs.append(args.preview)

    for key in jobs:
        try:
            generate_single(args.server, key, args.seed)
        except Exception as exc:
            print(f"[{key}] failed: {exc}", file=sys.stderr)
            sys.exit(1)

    if args.preview_bear:
        try:
            ref = make_bear_reference(args.server, args.seed)
            directions = {}
            for d in ["up", "right", "down", "left"]:
                directions[d] = make_bear_direction(args.server, d, ref, args.seed + hash(d) % 100000)
            assemble_bear_sheet(directions)
        except Exception as exc:
            print(f"[polar-bear] failed: {exc}", file=sys.stderr)
            sys.exit(1)

    if args.preview_tiles:
        try:
            make_tile_atlas(args.server, args.seed)
        except Exception as exc:
            print(f"[tiles] failed: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
