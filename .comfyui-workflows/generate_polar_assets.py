#!/usr/bin/env python3
"""
Generate the first batch of Polar Adventures assets via the local ComfyUI server.
Uses the z-image-turbo (AuraFlow) UNet with color-key transparency.
"""
import json
import requests
import sys
import time
from pathlib import Path

COMFYUI_URL = "http://note:8188"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets-src"

BACKGROUND_COLOR = 0xFF00FF  # magenta, for color-key transparency

PROMPTS = {
    # Polar bear direction stills. We generate one clean pose per cardinal direction.
    "polar_bear_north": (
        "cute polar bear standing, facing away from camera, north view, "
        "isometric game asset, simple low-poly style, clean outlines, "
        "solid magenta background #ff00ff, centered, full body visible, "
        "arctic white fur, soft shadows, high quality"
    ),
    "polar_bear_east": (
        "cute polar bear standing, facing right side view, east view, "
        "isometric game asset, simple low-poly style, clean outlines, "
        "solid magenta background #ff00ff, centered, full body visible, "
        "arctic white fur, soft shadows, high quality"
    ),
    "polar_bear_south": (
        "cute polar bear standing, facing toward camera, south front view, "
        "isometric game asset, simple low-poly style, clean outlines, "
        "solid magenta background #ff00ff, centered, full body visible, "
        "arctic white fur, soft shadows, high quality"
    ),
    "polar_bear_west": (
        "cute polar bear standing, facing left side view, west view, "
        "isometric game asset, simple low-poly style, clean outlines, "
        "solid magenta background #ff00ff, centered, full body visible, "
        "arctic white fur, soft shadows, high quality"
    ),
    # Terrain textures (square, will be post-processed into diamond tiles).
    "tile_snow": (
        "seamless snow texture, isometric arctic game tile, white powdery snow, "
        "subtle sparkles, flat lighting, solid magenta background #ff00ff, "
        "game asset, high quality"
    ),
    "tile_ice": (
        "seamless ice texture, isometric arctic game tile, frozen lake ice, "
        "glossy reflective surface, pale blue white, flat lighting, "
        "solid magenta background #ff00ff, game asset, high quality"
    ),
    "tile_ice_cracks": (
        "seamless cracked ice texture, isometric arctic game tile, "
        "frozen lake with dark cracks, pale blue white, flat lighting, "
        "solid magenta background #ff00ff, game asset, high quality"
    ),
}


def build_workflow():
    """Build an API-format ComfyUI workflow with shared model nodes."""
    workflow = {}

    # Shared model loading nodes.
    workflow["1"] = {
        "inputs": {
            "clip_name": "qwen_3_4b.safetensors",
            "type": "lumina2",
            "device": "default",
        },
        "class_type": "CLIPLoader",
    }
    workflow["2"] = {
        "inputs": {"vae_name": "ae.safetensors"},
        "class_type": "VAELoader",
    }
    workflow["3"] = {
        "inputs": {
            "unet_name": "z_image_turbo_bf16.safetensors",
            "weight_dtype": "default",
        },
        "class_type": "UNETLoader",
    }
    workflow["4"] = {
        "inputs": {"shift": 3, "model": ["3", 0]},
        "class_type": "ModelSamplingAuraFlow",
    }
    workflow["5"] = {
        "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
        "class_type": "EmptySD3LatentImage",
    }

    node_id = 10
    for key, prompt in PROMPTS.items():
        encode_id = str(node_id)
        zero_id = str(node_id + 1)
        sampler_id = str(node_id + 2)
        decode_id = str(node_id + 3)
        scale_id = str(node_id + 4)
        mask_id = str(node_id + 5)
        invert_id = str(node_id + 6)
        alpha_id = str(node_id + 7)
        save_id = str(node_id + 8)

        workflow[encode_id] = {
            "inputs": {"text": prompt, "clip": ["1", 0]},
            "class_type": "CLIPTextEncode",
        }
        workflow[zero_id] = {
            "inputs": {"conditioning": [encode_id, 0]},
            "class_type": "ConditioningZeroOut",
        }
        workflow[sampler_id] = {
            "inputs": {
                "seed": 0,
                "steps": 8,
                "cfg": 1,
                "sampler_name": "res_multistep",
                "scheduler": "simple",
                "denoise": 1,
                "model": ["4", 0],
                "positive": [encode_id, 0],
                "negative": [zero_id, 0],
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
                "width": 256,
                "height": 256,
                "crop": "center",
            },
            "class_type": "ImageScale",
        }
        workflow[mask_id] = {
            "inputs": {"image": [scale_id, 0], "color": BACKGROUND_COLOR},
            "class_type": "ImageColorToMask",
        }
        workflow[invert_id] = {
            "inputs": {"mask": [mask_id, 0]},
            "class_type": "InvertMask",
        }
        workflow[alpha_id] = {
            "inputs": {"image": [scale_id, 0], "alpha": [invert_id, 0]},
            "class_type": "JoinImageWithAlpha",
        }
        workflow[save_id] = {
            "inputs": {
                "filename_prefix": key,
                "images": [alpha_id, 0],
            },
            "class_type": "SaveImage",
        }

        node_id += 10

    return workflow


def queue_prompt(workflow):
    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_prompt(prompt_id, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        resp.raise_for_status()
        data = resp.json()
        if data:
            return data[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")


def download_outputs(history):
    outputs = history["outputs"]
    for node_id, node_outputs in outputs.items():
        for img in node_outputs.get("images", []):
            filename = img["filename"]
            subfolder = img.get("subfolder", "")
            url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type=output"
            resp = requests.get(url)
            resp.raise_for_status()
            out_path = OUTPUT_DIR / filename
            out_path.write_bytes(resp.content)
            print(f"saved: {out_path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    workflow = build_workflow()
    workflow_path = OUTPUT_DIR / "workflow_polar_assets.json"
    workflow_path.write_text(json.dumps(workflow, indent=2))
    print(f"workflow written to {workflow_path}")

    print("queueing prompt...")
    prompt_id = queue_prompt(workflow)
    print(f"prompt_id: {prompt_id}")

    print("waiting for completion...")
    history = wait_for_prompt(prompt_id)
    print("done")

    download_outputs(history)


if __name__ == "__main__":
    main()
