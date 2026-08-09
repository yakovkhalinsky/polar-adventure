#!/usr/bin/env python3
"""Queue ComfyUI prompts and assemble real game assets.

This script generates into public/assets/generated/ for review, then optionally
promotes them into the active asset folders. It produces one object at a time
with very strict prompts, and assembles the polar bear spritesheet from
individual direction frames.

Usage:
    python3 scripts/comfy_generate.py --server http://note:8188 --preview-all
    python3 scripts/comfy_generate.py --server http://note:8188 --preview-bear-3d
    python3 scripts/comfy_generate.py --server http://note:8188 --preview-bear-flat
    python3 scripts/comfy_generate.py --server http://note:8188 --promote
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import numpy as np
import requests
from PIL import Image, ImageFilter

try:
    from rembg import remove as rembg_remove
except Exception:
    rembg_remove = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public/assets"
PREVIEW = OUT / "generated"

BFL_BASE_URL = "https://api.bfl.ai"


VOXEL_LORA = "VoxelXL_v1.safetensors"
VOXEL_LORA_WEIGHT = 0.6


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


def require_tripo_nodes(server: str) -> None:
    """Exit with a helpful message if the Tripo custom nodes are not installed."""
    url = urljoin(server, "/object_info/TripoAPIDraft")
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        if resp.json().get("TripoAPIDraft"):
            return
    except Exception:
        pass
    print("ERROR: ComfyUI-Tripo nodes are not installed on the server.", file=sys.stderr)
    print("       Run one of the setup scripts:", file=sys.stderr)
    print("         .\\.comfyui-workflows\\setup_windows_comfyui.ps1", file=sys.stderr)
    print("       Then restart ComfyUI Desktop completely.", file=sys.stderr)
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

# Generic voxel style keywords. Objects avoid "isometric" because it pushes the model
# toward full scene/platform renders; characters still look fine with it.
VOXEL_STYLE_OBJECT = "voxel style, low poly, Fez-like, blocky 3D, cute "
VOXEL_STYLE_CHAR = "voxel style, low poly, Fez-like, blocky 3D, isometric, cute "

SINGLE_OBJECT = (
    "one single centered game asset, the asset is the main subject, "
    "pure white background, large empty white margin around it, "
    "floating object, no ground, no platform, no base, "
    "no text, no watermark, no border, no frame, isolated object"
)

NEGATIVE_OBJECT = (
    "platform, ground, base, pedestal, scene, landscape, environment, "
    "isometric scene, tile, block platform, water pool, grass patch, house, building, "
    "multiple objects, collage, shadow, reflection, blurry, low quality"
)


def make_object_prompt(subject: str) -> str:
    return f"{SINGLE_OBJECT}, {VOXEL_STYLE_OBJECT}, {subject}"


def make_character_prompt(subject: str) -> str:
    return f"{SINGLE_OBJECT}, {VOXEL_STYLE_CHAR}, {subject}"


ASSETS: dict[str, dict[str, Any]] = {
    "rock": {
        "prompt": make_object_prompt("grey arctic rock boulder, rough surface, small snow patches"),
        "size": 128,
        "out": PREVIEW / "objects/rock.png",
    },
    "iceberg": {
        "prompt": make_object_prompt("tall blue ice crystal chunk, translucent ice, white highlights"),
        "size": 128,
        "out": PREVIEW / "objects/iceberg.png",
    },
    "tree": {
        "prompt": make_object_prompt("snow covered pine tree, green needles, white snow cap"),
        "size": 128,
        "out": PREVIEW / "objects/tree.png",
    },
    "snow-mound": {
        "prompt": make_object_prompt("small mound of snow, smooth white surface, soft shadows"),
        "size": 128,
        "out": PREVIEW / "objects/snow-mound.png",
    },
    "igloo": {
        "prompt": make_object_prompt("single igloo dome, white ice blocks, small brown entrance"),
        "size": 128,
        "out": PREVIEW / "objects/igloo.png",
    },
    "sign": {
        "prompt": make_object_prompt("wooden signpost with blank board and snow on top, no text"),
        "size": 128,
        "out": PREVIEW / "objects/sign.png",
    },
    "fish": {
        "prompt": make_object_prompt("frozen arctic fish, red and silver scales, side view"),
        "size": 128,
        "out": PREVIEW / "objects/fish.png",
    },
    "penguin": {
        "prompt": make_character_prompt("cute cartoon penguin standing upright, black and white body, orange beak and feet"),
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


def upload_image(server: str, path: Path) -> str:
    """Upload a local image to ComfyUI's input folder and return the filename."""
    url = urljoin(server, "/upload/image")
    with path.open("rb") as f:
        resp = requests.post(
            url,
            files={"image": (path.name, f, "image/png")},
            data={"type": "input"},
            timeout=60,
        )
    resp.raise_for_status()
    data = resp.json()
    print(f"  uploaded {path} -> {data['name']}")
    return data["name"]


# ---------------------------------------------------------------------------
# Tripo 3D helpers
# ---------------------------------------------------------------------------


def tripo_bear_3d_workflow(image_name: str, api_key: str | None = None) -> dict[str, Any]:
    """ComfyUI prompt workflow that sends a bear reference image to Tripo image-to-3D.

    Requires the VAST-AI-Research/ComfyUI-Tripo custom nodes and a Tripo API key.
    Pass the key via the api_key argument, the TRIPO_API_KEY environment variable,
    or enter it directly in the node UI.
    """
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {"image": image_name},
        },
        "2": {
            "class_type": "TripoAPIDraft",
            "inputs": {
                "mode": "image_to_model",
                "apikey": api_key or "",
                "prompt": "",
                "negative_prompt": "",
                "image": ["1", 0],
                "model_version": "v3.0-20250812",
                "texture": True,
                "pbr": False,
                "image_seed": 42,
                "model_seed": 42,
                "texture_seed": 42,
                "texture_quality": "standard",
                "geometry_quality": "standard",
                "texture_alignment": "original_image",
                "face_limit": -1,
                "quad": False,
                "compress": False,
                "generate_parts": False,
                "smart_low_poly": False,
                "auto_size": False,
                "orientation": "align_image",
                "file_prefix": "polar-bear-3d",
                "output_directory": "",
            },
        },
        "3": {
            "class_type": "SaveText",
            "inputs": {
                "text": ["2", 0],
                "filename_prefix": "polar-bear-3d-path",
                "format": "txt",
            },
        },
    }



def extract_model_file_from_history(entry: dict[str, Any], node_id: str = "2") -> str | None:
    """Return the Tripo model_file path recorded in the prompt history."""
    outputs = entry.get("outputs", {})
    node_outputs = outputs.get(node_id, {})
    # The TripoAPIDraft node outputs a STRING at slot 0 named model_file.
    files = node_outputs.get("files", [])
    if files:
        return files[0].get("filename") or files[0].get("name")
    strings = node_outputs.get("string", [])
    if strings:
        return strings[0]
    # Fallback: some ComfyUI versions store plain lists.
    for key in ("model_file", "STRING"):
        if key in node_outputs:
            val = node_outputs[key]
            if isinstance(val, list):
                return val[0]
            return val
    return None


def make_bear_3d(server: str, reference: Path | None = None,
                 timeout: float = 600.0, api_key: str | None = None) -> Path:
    """Generate a textured GLB for the polar bear using Tripo image-to-3D."""
    reference = reference or PREVIEW / "characters/bear-reference-down.png"
    if not reference.exists():
        raise FileNotFoundError(f"Bear reference not found: {reference}")

    uploaded_name = upload_image(server, reference)
    workflow = tripo_bear_3d_workflow(uploaded_name, api_key=api_key)

    prompt_id = submit(server, workflow)
    print(f"[bear-3d] queued {prompt_id}")
    entry = poll_until_done(server, prompt_id, timeout=timeout)

    model_file = extract_model_file_from_history(entry, node_id="2")
    if not model_file:
        raise RuntimeError(f"Tripo node did not return a model_file path. History: {entry}")
    print(f"  Tripo model_file: {model_file}")

    # model_file may be a full path like ".../ComfyUI/output/polar-bear-3d_xxx.glb".
    path = Path(model_file)
    filename = path.name
    subfolder = str(path.parent.relative_to(Path("output"))) if "output" in path.parts else ""

    out = PREVIEW / "characters/polar-bear-3d.glb"
    download_image(server, filename, subfolder, out)
    print(f"  saved bear 3D preview to {out}")
    return out


# ---------------------------------------------------------------------------
# Black Forest Labs FLUX API helpers
# ---------------------------------------------------------------------------

def bfl_submit(api_key: str, prompt: str, width: int, height: int, seed: int,
               model: str = "flux-pro-1.1", **extra: Any) -> tuple[str, str]:
    """Submit a generation request to the BFL API and return (request_id, polling_url)."""
    url = urljoin(BFL_BASE_URL, f"/v1/{model}")
    payload: dict[str, Any] = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "seed": seed,
    }
    payload.update(extra)
    resp = requests.post(
        url,
        headers={"x-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    request_id = data.get("id") or data.get("request_id")
    polling_url = data.get("polling_url")
    if not request_id:
        raise RuntimeError(f"BFL submit returned no request id: {data}")
    print(f"  BFL {model} submitted: {request_id}")
    return str(request_id), polling_url


def bfl_poll_result(api_key: str, request_id: str,
                    polling_url: str | None = None,
                    timeout: float = 300.0) -> dict[str, Any]:
    """Poll the BFL result endpoint until the image is ready."""
    if polling_url is None:
        polling_url = urljoin(BFL_BASE_URL, "/v1/get_result")
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            polling_url,
            headers={"x-key": api_key},
            params={"id": request_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "")
        if status == "Ready":
            return data
        if status in ("Failed", "Error"):
            raise RuntimeError(f"BFL generation failed: {data}")
        print(f"  BFL status: {status}, waiting...")
        time.sleep(2.0)
    raise RuntimeError(f"BFL generation did not complete within {timeout}s")


def bfl_download_image(result: dict[str, Any], dest: Path) -> None:
    """Download the generated image from the BFL result to dest."""
    sample_url = result.get("result", {}).get("sample")
    if not sample_url:
        raise RuntimeError(f"BFL result has no sample URL: {result}")
    resp = requests.get(sample_url, timeout=120)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    print(f"  downloaded {dest}")


def _remove_white_fringe(arr: np.ndarray) -> np.ndarray:
    """After masking, decontaminate anti-aliased white edges.

    BFL/FLUX renders anti-aliased edges against white, leaving a light grey
    fringe when the white background is removed. This pass removes obvious
    white halo pixels and tries to recover the underlying color for soft edges.
    """
    height, width, _ = arr.shape
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    max_rgb = rgb.max(axis=2)
    min_rgb = rgb.min(axis=2)
    saturation = np.where(max_rgb > 0, (max_rgb - min_rgb) / max_rgb, 0)

    # Pixels that are light and desaturated are likely white-fringe contamination.
    fringe = (
        (alpha > 0)
        & (max_rgb > 230)
        & (saturation < 0.25)
    )

    # Estimate true alpha: 0 = white background, 1 = solid color.
    # For a grey fringe pixel, (255 - max_rgb)/255 approximates the colored
    # contribution. We keep pixels that have meaningful color, drop near-white.
    estimated_alpha = np.clip((255 - max_rgb) / 25.0, 0, 1)

    # Drop anything still too close to pure white.
    estimated_alpha[fringe & (max_rgb > 248)] = 0

    # Apply the refined alpha, but do not increase opacity.
    new_alpha = alpha * estimated_alpha / 255.0
    arr[:, :, 3] = np.clip(np.minimum(alpha, new_alpha * 255), 0, 255)
    return arr


def _isolate_white_bg_sprite(img: Image.Image) -> Image.Image:
    """Remove a near-pure white background using connected components + morphology.

    Best for BFL/FLUX images that come back with a clean white studio background.
    Keeps the largest foreground subject and fills internal holes.
    """
    rgba = img.convert("RGBA")
    arr = np.array(rgba).astype(np.float32)
    height, width, _ = arr.shape
    rgb = arr[:, :, :3]

    # Conservative threshold: only very light greys / white count as background.
    bg_mask = (rgb[:, :, 0] > 245) & (rgb[:, :, 1] > 245) & (rgb[:, :, 2] > 245)
    subject_mask = ~bg_mask

    # Dilate to bridge narrow gaps in white fur, then erode to tighten edges.
    mask_img = Image.fromarray((subject_mask * 255).astype(np.uint8))
    mask_img = mask_img.filter(ImageFilter.MaxFilter(7))
    mask_img = mask_img.filter(ImageFilter.MinFilter(5))
    mask = np.array(mask_img) > 128

    # Keep only the largest connected component.
    visited = np.zeros((height, width), bool)
    largest: list[tuple[int, int]] = []
    q: deque[tuple[int, int]] = deque()
    for y in range(height):
        for x in range(width):
            if mask[y, x] and not visited[y, x]:
                comp: list[tuple[int, int]] = []
                visited[y, x] = True
                q.append((y, x))
                while q:
                    cy, cx = q.popleft()
                    comp.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dy == 0 and dx == 0:
                                continue
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < height and 0 <= nx < width:
                                if mask[ny, nx] and not visited[ny, nx]:
                                    visited[ny, nx] = True
                                    q.append((ny, nx))
                if len(comp) > len(largest):
                    largest = comp

    if not largest:
        return rgba

    keep = np.zeros((height, width), bool)
    for y, x in largest:
        keep[y, x] = True

    # Fill holes by flood-filling background from the image border.
    holes = np.zeros((height, width), bool)
    for y in range(height):
        for x in (0, width - 1):
            if not keep[y, x] and not holes[y, x]:
                holes[y, x] = True
                q.append((y, x))
    for x in range(width):
        for y in (0, height - 1):
            if not keep[y, x] and not holes[y, x]:
                holes[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width:
                    if not keep[ny, nx] and not holes[ny, nx]:
                        holes[ny, nx] = True
                        q.append((ny, nx))

    keep = ~holes

    # Small final smoothing to remove white fringe artifacts.
    mask_img = Image.fromarray((keep * 255).astype(np.uint8))
    mask_img = mask_img.filter(ImageFilter.MaxFilter(3))
    mask_img = mask_img.filter(ImageFilter.MinFilter(3))
    keep = np.array(mask_img) > 128

    arr[~keep, 3] = 0
    arr = _remove_white_fringe(arr)
    return Image.fromarray(arr.astype(np.uint8))


def _isolate_unknown_bg_sprite(img: Image.Image) -> Image.Image:
    """Remove a non-white/colored/gradient background via adaptive flood fill."""
    rgba = img.convert("RGBA")
    arr = np.array(rgba).astype(np.float32)
    height, width, _ = arr.shape

    border: list[np.ndarray] = []
    for x in range(width):
        border.append(arr[0, x, :3])
        border.append(arr[height - 1, x, :3])
    for y in range(height):
        border.append(arr[y, 0, :3])
        border.append(arr[y, width - 1, :3])
    border_arr = np.array(border)
    seed = np.median(border_arr, axis=0)
    mad = np.median(np.abs(border_arr - seed).sum(axis=1))
    tol = max(55, int(mad * 3.0))

    bg = np.zeros((height, width), bool)
    q: deque[tuple[int, int]] = deque()
    for y in range(height):
        for x in (0, width - 1):
            if not bg[y, x] and np.abs(arr[y, x, :3] - seed).sum() < tol * 2:
                bg[y, x] = True
                q.append((y, x))
    for x in range(width):
        for y in (0, height - 1):
            if not bg[y, x] and np.abs(arr[y, x, :3] - seed).sum() < tol * 2:
                bg[y, x] = True
                q.append((y, x))

    while q:
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width and not bg[ny, nx]:
                    if np.abs(arr[ny, nx, :3] - seed).sum() < tol:
                        bg[ny, nx] = True
                        q.append((ny, nx))

    arr[bg, 3] = 0
    return Image.fromarray(arr.astype(np.uint8))


def _isolate_with_rembg(img: Image.Image) -> Image.Image | None:
    """Use the rembg U2Net model to remove the background, then clean the mask.

    rembg's alpha can be too aggressive on white fur, leaving semi-transparent
    "holes" inside the subject. We threshold the alpha more leniently, run
    morphological open/close to recover the subject, keep the largest connected
    component, and fill internal holes. Returns None if rembg is unavailable.
    """
    if rembg_remove is None:
        return None
    try:
        rgba = rembg_remove(img).convert("RGBA")
    except Exception:
        return None

    arr = np.array(rgba).astype(np.float32)
    height, width, _ = arr.shape
    rgb = arr[:, :, :3]

    # rembg returns soft alpha; be lenient so white fur isn't dropped.
    mask = arr[:, :, 3] > 20

    # Closing: dilate then erode with the same radius to bridge gaps in light
    # fur and connect the subject without shrinking it.
    mask_img = Image.fromarray((mask * 255).astype(np.uint8))
    mask_img = mask_img.filter(ImageFilter.MaxFilter(9))
    mask_img = mask_img.filter(ImageFilter.MinFilter(9))
    mask = np.array(mask_img) > 128

    # Keep largest connected component.
    visited = np.zeros((height, width), bool)
    largest: list[tuple[int, int]] = []
    q: deque[tuple[int, int]] = deque()
    for y in range(height):
        for x in range(width):
            if mask[y, x] and not visited[y, x]:
                comp: list[tuple[int, int]] = []
                visited[y, x] = True
                q.append((y, x))
                while q:
                    cy, cx = q.popleft()
                    comp.append((cy, cx))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dy == 0 and dx == 0:
                                continue
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < height and 0 <= nx < width:
                                if mask[ny, nx] and not visited[ny, nx]:
                                    visited[ny, nx] = True
                                    q.append((ny, nx))
                if len(comp) > len(largest):
                    largest = comp

    if not largest:
        return rgba

    keep = np.zeros((height, width), bool)
    for y, x in largest:
        keep[y, x] = True

    # Fill holes by flood-filling background from the image border.
    holes = np.zeros((height, width), bool)
    for y in range(height):
        for x in (0, width - 1):
            if not keep[y, x] and not holes[y, x]:
                holes[y, x] = True
                q.append((y, x))
    for x in range(width):
        for y in (0, height - 1):
            if not keep[y, x] and not holes[y, x]:
                holes[y, x] = True
                q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width:
                    if not keep[ny, nx] and not holes[ny, nx]:
                        holes[ny, nx] = True
                        q.append((ny, nx))

    keep = ~holes

    # Remove any ground shadow that rembg left at the bottom of the subject.
    # Shadow pixels are low-saturation grey, in the bottom ~12% of the bbox.
    max_rgb = rgb.max(axis=2)
    min_rgb = rgb.min(axis=2)
    saturation = np.where(max_rgb > 0, (max_rgb - min_rgb) / max_rgb, 0)

    coords = np.argwhere(keep)
    if len(coords) > 0:
        y1, _ = coords.min(axis=0)
        y2, _ = coords.max(axis=0) + 1
        bottom_cutoff = y1 + int((y2 - y1) * 0.88)
        is_shadow = (
            keep
            & (np.arange(height)[:, None] >= bottom_cutoff)
            & (saturation < 0.20)
            & (max_rgb > 40)
            & (max_rgb < 250)
        )

        # Only remove shadow connected to the bottom edge.
        visited = np.zeros((height, width), bool)
        shadow_to_remove = np.zeros((height, width), bool)
        for x in range(width):
            if is_shadow[height - 1, x] and not visited[height - 1, x]:
                visited[height - 1, x] = True
                q.append((height - 1, x))
                while q:
                    y, x = q.popleft()
                    shadow_to_remove[y, x] = True
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < height and 0 <= nx < width:
                            if is_shadow[ny, nx] and not visited[ny, nx]:
                                visited[ny, nx] = True
                                q.append((ny, nx))

        keep = keep & ~shadow_to_remove

    # Final smoothing.
    mask_img = Image.fromarray((keep * 255).astype(np.uint8))
    mask_img = mask_img.filter(ImageFilter.MaxFilter(3))
    mask_img = mask_img.filter(ImageFilter.MinFilter(3))
    keep = np.array(mask_img) > 128

    arr[~keep, 3] = 0
    return Image.fromarray(arr.astype(np.uint8))


def isolate_largest_sprite(img: Image.Image, target_size: int, raw_path: Path | None = None,
                           force_rembg: bool = False) -> Image.Image:
    """Crop to the largest foreground region and make the background transparent.

    Auto-detects a near-pure white background (typical of BFL/FLUX output) and uses
    rembg when available for clean shadow removal. Falls back to a fast morphological
    mask, then to adaptive flood fill for colored/gradient backgrounds.
    """
    rgba = img.convert("RGBA")
    if raw_path is not None:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        rgba.save(raw_path)

    arr = np.array(rgba).astype(np.float32)
    height, width, _ = arr.shape

    # Decide strategy from the border pixels.
    border: list[np.ndarray] = []
    for x in range(width):
        border.append(arr[0, x, :3])
        border.append(arr[height - 1, x, :3])
    for y in range(height):
        border.append(arr[y, 0, :3])
        border.append(arr[y, width - 1, :3])
    border_arr = np.array(border)
    mostly_white = np.all(border_arr > 250, axis=1).mean() > 0.95

    isolated: Image.Image | None = None
    if (mostly_white or force_rembg) and rembg_remove is not None:
        isolated = _isolate_with_rembg(rgba)

    if isolated is None:
        if mostly_white:
            isolated = _isolate_white_bg_sprite(rgba)
        else:
            isolated = _isolate_unknown_bg_sprite(rgba)

    # Crop to the non-transparent bounding box.
    alpha = np.array(isolated.split()[-1])
    coords = np.argwhere(alpha > 0)
    if len(coords) == 0:
        return Image.new("RGBA", (target_size, target_size), (255, 255, 255, 0))
    y1, x1 = coords.min(axis=0)
    y2, x2 = coords.max(axis=0) + 1
    crop = isolated.crop((x1, y1, x2, y2))

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

    negative = f"{NEGATIVE_SPRITE}, {NEGATIVE_OBJECT}"
    if use_img2img and guide and guide.exists():
        workflow = img2img_workflow(gen_size, gen_size, prompt, negative, seed, guide, denoise=0.55)
    else:
        workflow = base_workflow(gen_size, gen_size, prompt, negative, seed)

    prompt_id = submit(server, workflow)
    print(f"[{key}] queued {prompt_id}")
    entry = poll_until_done(server, prompt_id)
    images = entry.get("outputs", {}).get("7", {}).get("images", [])
    if not images:
        raise RuntimeError(f"No images returned for {key}")

    download_image(server, images[0]["filename"], images[0].get("subfolder", ""), spec["out"])

    with Image.open(spec["out"]).convert("RGBA") as img:
        isolated = isolate_largest_sprite(img, size, raw_path=spec["out"].with_suffix(".raw.png"))
        isolated.save(spec["out"])
        print(f"  isolated -> {size}x{size}")

    return spec["out"]


def make_bear_reference(server: str | None, seed: int, size: int = 512,
                        direction: str = "down",
                        style_ref: Path | None = None,
                        use_sd15: bool = False,
                        bfl_api_key: str | None = None,
                        bfl_model: str = "flux-pro-1.1",
                        flat_style: bool = False) -> Path:
    """Generate a single consistent adult polar bear reference on white for a given direction.

    If bfl_api_key is provided, the Black Forest Labs FLUX API is used instead of ComfyUI.
    If style_ref is provided, it is uploaded to ComfyUI and used as the img2img init image so the
    generated frame inherits the reference's colors, outfit, proportions, and style.
    If use_sd15 is True, the SD 1.5 checkpoint is used instead of CartoonXL SDXL.
    If flat_style is True, the prompt asks for a flat vector isometric sprite style.
    """
    direction_prompts = {
        "up": "seen from behind, back view, walking away from camera, facing away",
        "right": "side view facing right, walking to the right, profile view",
        "down": "front view facing camera, walking toward viewer",
        "left": "side view facing left, walking to the left, profile view",
    }

    if flat_style:
        prompt = (
            "flat vector game character, polar bear anthropomorphic adult male, clean thick dark outline, "
            "simple geometric shapes, minimal shading, solid flat colors, "
            "wearing a solid grey hoodie with drawstrings and plain blue denim jeans with no rips, no tears, no holes, intact denim, "
            "white fur, black and white high-top sneakers like Converse Chuck Taylors, bare hands with visible claws, no gloves, no headband, "
            f"{direction_prompts[direction]}, "
            "isometric game asset, pure white background, isolated character, centered, "
            "no text, no watermark, no border, no shadows, no gradients"
        )
        negative = (
            f"{NEGATIVE_SPRITE}, {NEGATIVE_OBJECT}, baby, cub, child, toddler, chibi, kawaii, "
            "cute, big eyes, large eyes, round face, big head, short legs, stubby legs, "
            "belly, overweight, chubby, gloves, mittens, wrist cuffs, "
            "barefoot, bare paws, no shoes, sandals, boots, high heels, "
            "white hoodie, black hoodie, blue hoodie, pink hoodie, red hoodie, "
            "ripped jeans, torn jeans, distressed jeans, holes in jeans, frayed jeans, shorts, skirt, bare chest, "
            "3d rendered, realistic, photograph, smooth shading, detailed fabric, texture, soft shadows, "
            "grey background, gradient background, textured background"
        )
    else:
        prompt = (
            "anthropomorphic adult male polar bear character, smooth 3D rendered style, soft realistic shading, "
            "detailed fabric texture, muscular humanoid build, broad muscular shoulders, thick arms, strong stocky body, "
            "wearing a solid grey hoodie with drawstrings and plain blue denim jeans with no rips, "
            "white fur, black and white high-top sneakers like Converse Chuck Taylors, bare hands with visible claws, no gloves, no headband, "
            f"{direction_prompts[direction]}, "
            "pure white background, isolated character, centered, "
            "no text, no watermark, no border"
        )
        negative = (
            f"{NEGATIVE_SPRITE}, {NEGATIVE_OBJECT}, baby, cub, child, toddler, chibi, kawaii, "
            "cute, big eyes, large eyes, round face, big head, short legs, stubby legs, "
            "belly, overweight, chubby, gloves, mittens, wrist cuffs, "
            "barefoot, bare paws, no shoes, sandals, boots, high heels, "
            "white hoodie, black hoodie, blue hoodie, pink hoodie, red hoodie, "
            "ripped jeans, torn jeans, distressed jeans, shorts, skirt, bare chest, "
            "cartoon, anime, mascot, plushie, toy, figurine, Funko, collectable, "
            "flat shading, 2d illustration, grey background, gradient background, textured background, photograph"
        )
    out = PREVIEW / f"characters/bear-reference-{direction}.png"

    if bfl_api_key:
        # BFL supports square generation well; use 1024x1024 for detail.
        request_id, polling_url = bfl_submit(bfl_api_key, prompt, 1024, 1024, seed, model=bfl_model)
        result = bfl_poll_result(bfl_api_key, request_id, polling_url=polling_url)
        bfl_download_image(result, out)
        with Image.open(out).convert("RGBA") as img:
            isolate_largest_sprite(img, size, raw_path=out.with_suffix(".raw.png")).save(out)
        return out

    if server is None:
        raise ValueError("No ComfyUI server provided and no BFL API key set")

    if use_sd15:
        checkpoint = "v1-5-pruned-emaonly.safetensors"
        width, height, gen_steps, gen_cfg = 512, 512, 35, 7.5
    else:
        checkpoint = "cartoonxl_v10.safetensors"
        width, height, gen_steps, gen_cfg = 1024, 1024, 40, 9.0

    if style_ref is not None and style_ref.exists():
        uploaded_name = upload_image(server, style_ref)
        # Low denoise preserves the reference style/outfit; prompt steers direction.
        workflow = img2img_workflow(
            width, height, prompt, negative, seed, Path(uploaded_name),
            denoise=0.35, checkpoint=checkpoint, steps=gen_steps, cfg=gen_cfg, lora_name=None,
        )
    else:
        workflow = base_workflow(width, height, prompt, negative, seed,
                                 checkpoint=checkpoint, steps=gen_steps, cfg=gen_cfg, lora_name=None)

    prompt_id = submit(server, workflow)
    print(f"[bear-reference-{direction}] queued {prompt_id}")
    entry = poll_until_done(server, prompt_id)
    images = entry.get("outputs", {}).get("7", {}).get("images", [])
    download_image(server, images[0]["filename"], images[0].get("subfolder", ""), out)
    with Image.open(out).convert("RGBA") as img:
        isolate_largest_sprite(img, size, raw_path=out.with_suffix(".raw.png")).save(out)
    return out


def make_bear_direction(server: str, direction: str, reference: Path, seed: int,
                        pose: str = "", use_sd15: bool = False, flat_style: bool = False) -> Path:
    """Generate one direction frame using img2img from the reference for consistency."""
    directions = {
        "up": "seen from behind, walking away, back view, facing away, upright humanoid posture",
        "right": "side view walking to the right, facing right, upright humanoid posture",
        "left": "side view walking to the left, facing left, upright humanoid posture",
        "down": "front view walking toward viewer, facing camera, upright humanoid posture",
    }

    if flat_style:
        prompt = (
            "flat vector game character, same polar bear anthropomorphic design and outfit as reference, "
            "clean thick dark outline, simple geometric shapes, minimal shading, solid flat colors, "
            "wearing a solid grey hoodie with drawstrings and plain blue denim jeans with no rips, "
            "white fur, black and white high-top sneakers like Converse Chuck Taylors, bare hands with visible claws, no gloves, no headband, "
            f"{directions[direction]}, {pose}, "
            "isometric game asset, pure white background, isolated character, centered, "
            "no text, no watermark, no border, no shadows, no gradients"
        )
        negative = (
            f"{NEGATIVE_SPRITE}, {NEGATIVE_OBJECT}, baby, cub, child, toddler, chibi, kawaii, "
            "cute, big eyes, large eyes, round face, big head, short legs, stubby legs, "
            "belly, overweight, chubby, gloves, mittens, wrist cuffs, "
            "barefoot, bare paws, no shoes, sandals, boots, high heels, "
            "white hoodie, black hoodie, blue hoodie, pink hoodie, red hoodie, "
            "ripped jeans, torn jeans, distressed jeans, shorts, skirt, bare chest, "
            "3d rendered, realistic, photograph, smooth shading, detailed fabric, texture, soft shadows, "
            "grey background, gradient background, textured background"
        )
    else:
        prompt = (
            "anthropomorphic adult male polar bear character, same smooth 3D design and outfit as reference, "
            "soft realistic shading, detailed fabric texture, muscular humanoid build, broad muscular shoulders, thick arms, strong stocky body, "
            "wearing a solid grey hoodie with drawstrings and plain blue denim jeans with no rips, "
            "white fur, black and white high-top sneakers like Converse Chuck Taylors, bare hands with visible claws, no gloves, no headband, "
            f"{directions[direction]}, {pose}, "
            "pure white background, isolated character, centered, "
            "no text, no watermark, no border"
        )
        negative = (
            f"{NEGATIVE_SPRITE}, {NEGATIVE_OBJECT}, baby, cub, child, toddler, chibi, kawaii, "
            "cute, big eyes, large eyes, round face, big head, short legs, stubby legs, "
            "belly, overweight, chubby, gloves, mittens, wrist cuffs, "
            "barefoot, bare paws, no shoes, sandals, boots, high heels, "
            "white hoodie, black hoodie, blue hoodie, pink hoodie, red hoodie, "
            "ripped jeans, torn jeans, distressed jeans, shorts, skirt, bare chest, "
            "cartoon, anime, mascot, plushie, toy, figurine, Funko, collectable, "
            "flat shading, 2d illustration, grey background, gradient background, textured background, photograph"
        )
    out = PREVIEW / f"characters/bear-{direction}-{seed}.png"

    uploaded_name = upload_image(server, reference)

    if use_sd15:
        # SD 1.5 works at 512x512 with the uploaded reference, low denoise keeps the style/outfit.
        workflow = img2img_workflow(
            512, 512, prompt, negative, seed, Path(uploaded_name),
            denoise=0.45, checkpoint="v1-5-pruned-emaonly.safetensors",
            steps=30, cfg=7.5, lora_name=None,
        )
    else:
        workflow = img2img_workflow(1024, 1024, prompt, negative, seed, Path(uploaded_name), denoise=0.55)

    prompt_id = submit(server, workflow)
    print(f"[bear-{direction}-{seed}] queued {prompt_id}")
    entry = poll_until_done(server, prompt_id)
    images = entry.get("outputs", {}).get("7", {}).get("images", [])
    download_image(server, images[0]["filename"], images[0].get("subfolder", ""), out)

    with Image.open(out).convert("RGBA") as img:
        isolate_largest_sprite(img, 512, raw_path=out.with_suffix(".raw.png")).save(out)
        print(f"  isolated bear-{direction}-{seed}")

    return out


def assemble_bear_sheet(directions: dict[str, list[Path]], rows: int = 8) -> Path:
    """Assemble a polar bear spritesheet.

    By default (rows=8) produces the full 4 directions x 8 rows sheet used by the
    realistic 3D pipeline. When rows=4 and directions contains one frame per
    direction, produces a compact 4x4 flat-vector sheet: walk-up, walk-right,
    walk-down, walk-left.
    """
    cell = 128
    cols = 4
    sheet = Image.new("RGBA", (cell * cols, cell * rows), (255, 255, 255, 0))

    order = ["up", "right", "down", "left"]
    frames: dict[str, list[Image.Image]] = {}
    for d in order:
        frames[d] = []
        for path in directions[d]:
            img = Image.open(path).convert("RGBA")
            # Scale/crop to cell, keeping centered.
            scale = cell / max(img.size)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            frame = Image.new("RGBA", (cell, cell), (255, 255, 255, 0))
            x = (cell - img.width) // 2
            y = (cell - img.height) // 2
            frame.paste(img, (x, y), img)
            frames[d].append(frame)

    if rows == 4:
        # Compact flat-vector sheet: one row per direction, 4 identical frames.
        for row, d in enumerate(order):
            frame = frames[d][0]
            for col in range(cols):
                sheet.paste(frame, (col * cell, row * cell), frame)
    else:
        # Row mapping for walk directions.
        row_dirs = ["up", "right", "down", "left", "down", "down", "down", "down"]
        for row, d in enumerate(row_dirs):
            direction_frames = frames[d]
            for col in range(cols):
                frame = direction_frames[col % len(direction_frames)]
                sheet.paste(frame, (col * cell, row * cell), frame)

    out = PREVIEW / "characters/polar-bear.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"  assembled {out}")
    return out


def make_bear_reference_preview(server: str, seed: int,
                                style_ref: Path | None = None,
                                use_sd15: bool = False,
                                flat_style: bool = False) -> Path:
    """Generate a front-facing reference and build a preview sheet that repeats it."""
    ref = make_bear_reference(server, seed, direction="down", style_ref=style_ref,
                              use_sd15=use_sd15, flat_style=flat_style)
    return _make_preview_sheet_from_ref(ref, rows=4 if flat_style else 8)


def make_bear_reference_preview_with_ref(ref: Path) -> Path:
    """Build a preview sheet from an already-generated reference file."""
    return _make_preview_sheet_from_ref(ref)


def _make_preview_sheet_from_ref(ref: Path, rows: int = 8) -> Path:
    """Tile a 512x512 reference into a 4xN preview sheet (default 8, flat mode uses 4)."""
    with Image.open(ref).convert("RGBA") as img:
        cell = 128
        scale = cell / max(img.size)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        frame = Image.new("RGBA", (cell, cell), (255, 255, 255, 0))
        x = (cell - img.width) // 2
        y = (cell - img.height) // 2
        frame.paste(img, (x, y), img)

    sheet = Image.new("RGBA", (cell * 4, cell * rows), (255, 255, 255, 0))
    for row in range(rows):
        for col in range(4):
            sheet.paste(frame, (col * cell, row * cell), frame)

    out = PREVIEW / "characters/polar-bear-preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"  assembled preview {out}")
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
    parser.add_argument("--preview-bear-flat", action="store_true", help="Generate flat vector polar bear reference + 4x4 spritesheet")
    parser.add_argument("--preview-bear-ref", action="store_true", help="Generate front-facing reference preview sheet only")
    parser.add_argument("--preview-bear-3d", action="store_true", help="Generate a textured GLB of the polar bear via Tripo image-to-3D")
    parser.add_argument("--preview-tiles", action="store_true", help="Generate tile atlas")
    parser.add_argument("--promote", action="store_true", help="Copy previews to active asset folders")
    parser.add_argument("--no-lora", action="store_true", help="Use CartoonXL without the Voxel XL LoRA (not voxel style)")
    parser.add_argument("--lora-weight", type=float, default=None, help="Override Voxel XL LoRA strength (default 0.6)")
    parser.add_argument("--sd15", action="store_true", help="Use the SD 1.5 checkpoint instead of CartoonXL SDXL for bear generation")
    parser.add_argument("--style-ref", type=Path, default=None, help="Image to use as an img2img style/outfit reference for bear generation")
    parser.add_argument("--bfl", action="store_true", help="Use the Black Forest Labs FLUX API instead of ComfyUI")
    parser.add_argument("--bfl-model", default="flux-pro-1.1", help="BFL model to use (default: flux-pro-1.1)")
    parser.add_argument("--bfl-api-key", default=None, help="BFL API key (defaults to BFL_API_KEY env var)")
    parser.add_argument("--tripo-api-key", default=None, help="Tripo API key (defaults to TRIPO_API_KEY env var)")
    args = parser.parse_args()

    if args.no_lora:
        global VOXEL_LORA
        VOXEL_LORA = None
    elif args.lora_weight is not None:
        global VOXEL_LORA_WEIGHT
        VOXEL_LORA_WEIGHT = args.lora_weight

    if args.promote:
        promote()
        return

    bfl_api_key = args.bfl_api_key or os.environ.get("BFL_API_KEY")

    if not args.bfl:
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

    if args.preview_bear or args.preview_bear_flat:
        flat_style = args.preview_bear_flat
        if args.bfl and not bfl_api_key:
            print("ERROR: --bfl requires --bfl-api-key or BFL_API_KEY env var", file=sys.stderr)
            sys.exit(1)
        try:
            server = None if args.bfl else args.server
            # Generate a direction-specific reference for each cardinal direction so the
            # silhouettes actually read as up/right/down/left in the final sheet.
            refs: dict[str, Path] = {}
            for d in ["up", "right", "down", "left"]:
                refs[d] = make_bear_reference(
                    server, args.seed, direction=d,
                    style_ref=args.style_ref, use_sd15=args.sd15,
                    bfl_api_key=bfl_api_key, bfl_model=args.bfl_model,
                    flat_style=flat_style,
                )

            directions: dict[str, list[Path]] = {}
            if flat_style:
                # Flat vector style: one static pose per direction, reuse for all 4 frames.
                for d in ["up", "right", "down", "left"]:
                    directions[d] = [refs[d]]
                assemble_bear_sheet(directions, rows=4)
            else:
                # Realistic 3D style: two alternating walk poses per direction.
                for d in ["up", "right", "down", "left"]:
                    pose_a = make_bear_direction(
                        args.server, d, refs[d], args.seed + hash(d) % 100000,
                        pose="left leg forward, right leg back, left arm back, right arm forward",
                        use_sd15=args.sd15,
                    )
                    pose_b = make_bear_direction(
                        args.server, d, refs[d], args.seed + hash(d) % 100000 + 50000,
                        pose="right leg forward, left leg back, right arm back, left arm forward",
                        use_sd15=args.sd15,
                    )
                    directions[d] = [pose_a, pose_b]
                assemble_bear_sheet(directions, rows=8)
        except Exception as exc:
            print(f"[polar-bear] failed: {exc}", file=sys.stderr)
            sys.exit(1)

    if args.preview_bear_ref:
        flat_style = args.preview_bear_flat
        if args.bfl and not bfl_api_key:
            print("ERROR: --bfl requires --bfl-api-key or BFL_API_KEY env var", file=sys.stderr)
            sys.exit(1)
        try:
            server = None if args.bfl else args.server
            ref = make_bear_reference(
                server, args.seed, direction="down",
                style_ref=args.style_ref, use_sd15=args.sd15,
                bfl_api_key=bfl_api_key, bfl_model=args.bfl_model,
                flat_style=flat_style,
            )
            make_bear_reference_preview_with_ref(ref, rows=4 if flat_style else 8)
        except Exception as exc:
            print(f"[bear-reference-preview] failed: {exc}", file=sys.stderr)
            sys.exit(1)

    if args.preview_bear_3d:
        require_tripo_nodes(args.server)
        tripo_api_key = args.tripo_api_key or os.environ.get("TRIPO_API_KEY")
        if not tripo_api_key:
            print("WARN: Tripo API key is not set. The Tripo node may fail unless the key is entered in its UI widget.", file=sys.stderr)
            print("       Set TRIPO_API_KEY or pass --tripo-api-key.", file=sys.stderr)
        try:
            make_bear_3d(args.server, reference=args.style_ref, timeout=900.0, api_key=tripo_api_key)
        except Exception as exc:
            print(f"[bear-3d] failed: {exc}", file=sys.stderr)
            sys.exit(1)

    if args.preview_tiles:
        try:
            make_tile_atlas(args.server, args.seed)
        except Exception as exc:
            print(f"[tiles] failed: {exc}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
