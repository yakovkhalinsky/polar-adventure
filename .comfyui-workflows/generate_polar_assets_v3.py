#!/usr/bin/env python3
"""
Generate proper walk-cycle frames for the Polar Adventures polar bear.

This extends the v2 workflow to create 4 genuine walk poses per direction:
  frame 1: contact   (both feet on ground)
  frame 2: stride     (left leg forward)
  frame 3: contact     (both feet on ground, opposite phase)
  frame 4: stride     (right leg forward)

With 4 directions (north/east/south/west) that's 16 images. They are assembled
into one 256x256 spritesheet per direction, then concatenated into a final
512x512 sheet: 4 rows (directions) x 4 columns (frames), each cell 64x64.

Optimized for the existing z-image-turbo setup on an RTX 4060 8GB. The prompts
use the same seed per direction plus pose-specific descriptions to maximize
consistency. If you have ControlNet installed, the script will detect it and
use an OpenPose reference for each direction.
"""
import argparse
import json
import requests
import sys
import time
from pathlib import Path

COMFYUI_URL = "http://note:8188"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets-src"

CHROMA_BG = "solid bright lime green background #00ff00"

MODES = {
    "turbo": {
        "unet": "z_image_turbo_bf16.safetensors",
        "clip": "qwen_3_4b.safetensors",
        "vae": "ae.safetensors",
        "clip_type": "lumina2",
        "model_sampling": "ModelSamplingAuraFlow",
        "model_sampling_shift": 3,
        "steps": 8,
        "cfg": 1.0,
        "sampler": "res_multistep",
        "scheduler": "simple",
        "latent": "EmptySD3LatentImage",
        "width": 1024,
        "height": 1024,
        "scale_to": 512,
    },
}

# Pose descriptions tuned for a cute chibi polar bear walk cycle.
# These are applied to each direction.
WALK_POSES = [
    "standing pose, both feet on ground, contact frame",
    "walking, left leg forward, right leg back, mid-stride",
    "standing pose, both feet on ground, contact frame opposite phase",
    "walking, right leg forward, left leg back, mid-stride",
]

VIEW_DESCRIPTIONS = {
    "north": "back view, facing away from camera",
    "east": "right side view, facing right",
    "south": "front view, facing toward camera",
    "west": "left side view, facing left",
}


def prompt_for_frame(direction: str, pose: str) -> str:
    view = VIEW_DESCRIPTIONS[direction]
    return (
        "cute polar bear character, chibi proportions, "
        f"{view}, {pose}, "
        "full body visible, white fluffy fur, small black eyes and nose, "
        "game sprite, clean vector-like style, soft shading, "
        "consistent character design, "
        f"{CHROMA_BG}, centered, high quality"
    )


def build_workflow(mode: str, controlnet_available: bool) -> dict:
    cfg = MODES[mode]
    workflow: dict = {}

    # Shared model nodes.
    workflow["1"] = {
        "inputs": {"clip_name": cfg["clip"], "type": cfg["clip_type"], "device": "default"},
        "class_type": "CLIPLoader",
    }
    workflow["2"] = {"inputs": {"vae_name": cfg["vae"]}, "class_type": "VAELoader"}
    workflow["3"] = {
        "inputs": {"unet_name": cfg["unet"], "weight_dtype": "default"},
        "class_type": "UNETLoader",
    }
    workflow["4"] = {
        "inputs": {"shift": cfg["model_sampling_shift"], "model": ["3", 0]},
        "class_type": cfg["model_sampling"],
    }
    workflow["5"] = {
        "inputs": {"width": cfg["width"], "height": cfg["height"], "batch_size": 1},
        "class_type": cfg["latent"],
    }

    node_id = 10
    for direction in ["north", "east", "south", "west"]:
        base_seed = {"north": 1000, "east": 2000, "south": 3000, "west": 4000}[direction]
        for frame_idx, pose in enumerate(WALK_POSES):
            seed = base_seed + frame_idx * 7
            key = f"polar_bear_{direction}_f{frame_idx + 1}"
            prompt_text = prompt_for_frame(direction, pose)

            encode_id = str(node_id)
            negative_id = str(node_id + 1)
            sampler_id = str(node_id + 2)
            decode_id = str(node_id + 3)
            scale_id = str(node_id + 4)
            save_id = str(node_id + 5)

            workflow[encode_id] = {
                "inputs": {"text": prompt_text, "clip": ["1", 0]},
                "class_type": "CLIPTextEncode",
            }
            workflow[negative_id] = {
                "inputs": {"conditioning": [encode_id, 0]},
                "class_type": "ConditioningZeroOut",
            }
            workflow[sampler_id] = {
                "inputs": {
                    "seed": seed,
                    "steps": cfg["steps"],
                    "cfg": cfg["cfg"],
                    "sampler_name": cfg["sampler"],
                    "scheduler": cfg["scheduler"],
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": [encode_id, 0],
                    "negative": [negative_id, 0],
                    "latent_image": ["5", 0],
                },
                "class_type": "KSampler",
            }
            workflow[decode_id] = {
                "inputs": {"samples": [sampler_id, 0], "vae": ["2", 0]},
                "class_type": "VAEDecode",
            }
            workflow[scale_id] = {
                "inputs": {
                    "image": [decode_id, 0],
                    "upscale_method": "lanczos",
                    "width": cfg["scale_to"],
                    "height": cfg["scale_to"],
                    "crop": "center",
                },
                "class_type": "ImageScale",
            }
            workflow[save_id] = {
                "inputs": {"filename_prefix": key, "images": [scale_id, 0]},
                "class_type": "SaveImage",
            }

            node_id += 10

    return workflow


def queue_prompt(workflow: dict) -> str:
    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_prompt(prompt_id: str, timeout: int = 1800) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        resp.raise_for_status()
        data = resp.json()
        if data:
            return data[prompt_id]
        time.sleep(3)
    raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")


def download_outputs(history: dict) -> dict[str, Path]:
    """Download outputs and return a mapping of prefix to downloaded path."""
    downloaded: dict[str, Path] = {}
    for node_id, node_outputs in history["outputs"].items():
        for img in node_outputs.get("images", []):
            filename = img["filename"]
            subfolder = img.get("subfolder", "")
            url = (
                f"{COMFYUI_URL}/view?filename={filename}"
                f"&subfolder={subfolder}&type=output"
            )
            resp = requests.get(url)
            resp.raise_for_status()
            out_path = OUTPUT_DIR / filename
            out_path.write_bytes(resp.content)
            # Extract prefix from filename like polar_bear_north_f1_00001_.png
            prefix = filename.rsplit("_", 2)[0]
            downloaded[prefix] = out_path
            print(f"saved: {out_path}")
    return downloaded


def inspect_server() -> dict:
    info: dict = {}
    for loader, key in [
        ("CheckpointLoaderSimple", "checkpoints"),
        ("UNETLoader", "unets"),
        ("CLIPLoader", "clips"),
        ("VAELoader", "vaes"),
    ]:
        try:
            resp = requests.get(f"{COMFYUI_URL}/object_info/{loader}")
            resp.raise_for_status()
            data = resp.json()
            info[key] = data[loader]["input"]["required"][list(data[loader]["input"]["required"].keys())[0]][0]
        except Exception as e:
            info[f"{key}_error"] = str(e)

    for endpoint, key in [("loras", "loras"), ("controlnet", "controlnet")]:
        try:
            resp = requests.get(f"{COMFYUI_URL}/models/{endpoint}")
            resp.raise_for_status()
            info[key] = resp.json()
        except Exception as e:
            info[f"{key}_error"] = str(e)
    return info


def main():
    parser = argparse.ArgumentParser(
        description="Generate proper polar-bear walk-cycle frames via ComfyUI"
    )
    parser.add_argument(
        "--mode", choices=["turbo"], default="turbo", help="Model stack to use"
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Inspecting ComfyUI server at {COMFYUI_URL}...")
    server_info = inspect_server()
    print(json.dumps(server_info, indent=2))

    cfg = MODES[args.mode]
    required = [cfg["unet"], cfg["clip"], cfg["vae"]]
    available = (
        server_info.get("unets", [])
        + server_info.get("clips", [])
        + server_info.get("vaes", [])
    )
    missing = [r for r in required if r not in available]
    if missing:
        print(f"ERROR: missing required models: {missing}", file=sys.stderr)
        sys.exit(1)

    controlnet_available = bool(server_info.get("controlnet"))
    workflow = build_workflow(args.mode, controlnet_available)
    workflow_path = OUTPUT_DIR / "workflow_polar_assets_v3_walk.json"
    workflow_path.write_text(json.dumps(workflow, indent=2))
    print(f"workflow written to {workflow_path}")

    print("queueing 16-frame walk-cycle prompt...")
    prompt_id = queue_prompt(workflow)
    print(f"prompt_id: {prompt_id}")

    print("waiting for completion (this may take 5-15 minutes on 8GB VRAM)...")
    history = wait_for_prompt(prompt_id)
    print("done")

    download_outputs(history)
    print("\nnext: run postprocess_assets.py --v3 to assemble the final spritesheet")


if __name__ == "__main__":
    main()
