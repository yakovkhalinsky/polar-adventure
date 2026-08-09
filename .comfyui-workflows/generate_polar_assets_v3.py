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

Optimized for an RTX 4060 8GB. The default mode is now SD 1.5 because it leaves
enough VRAM for LoRAs, ControlNet, and transparent-background nodes. The legacy
turbo mode is kept for the AuraFlow setup if desired.
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
    "sd15": {
        "checkpoint": "v1-5-pruned-emaonly.safetensors",
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "steps": 25,
        "cfg": 7.5,
        "width": 512,
        "height": 512,
        "scale_to": 512,
        "negative": "low quality, blurry, deformed, extra limbs, watermark, signature, text, cropped, worst quality",
        "loader": "CheckpointLoaderSimple",
    },
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
        "negative": None,
        "loader": "UNETLoader",
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

TILE_DESCRIPTIONS = {
    "snow": "flat isometric diamond floor tile, soft white snow surface, subtle texture, arctic landscape, game asset, " + CHROMA_BG + ", centered, high quality",
    "ice": "flat isometric diamond floor tile, smooth reflective blue ice surface, arctic glacier, game asset, " + CHROMA_BG + ", centered, high quality",
    "ice_cracks": "flat isometric diamond floor tile, cracked ice surface with deep blue fissures, arctic glacier, game asset, " + CHROMA_BG + ", centered, high quality",
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


def build_sd15_workflow(controlnet_available: bool, lora_name: str | None) -> dict:
    cfg = MODES["sd15"]
    workflow: dict = {}

    # Shared checkpoint.
    workflow["1"] = {
        "inputs": {"ckpt_name": cfg["checkpoint"]},
        "class_type": "CheckpointLoaderSimple",
    }

    # Optional LoRA for style consistency.
    last_model = ["1", 0]
    last_clip = ["1", 1]
    node_id = 2
    if lora_name:
        workflow[str(node_id)] = {
            "inputs": {
                "lora_name": lora_name,
                "strength_model": 0.7,
                "strength_clip": 0.7,
                "model": last_model,
                "clip": last_clip,
            },
            "class_type": "LoraLoader",
        }
        last_model = [str(node_id), 0]
        last_clip = [str(node_id), 1]
        node_id += 1

    workflow[str(node_id)] = {
        "inputs": {
            "width": cfg["width"],
            "height": cfg["height"],
            "batch_size": 1,
        },
        "class_type": "EmptyLatentImage",
    }
    latent_id = node_id
    node_id += 1

    # Shared negative prompt encoder.
    encode_neg_id = node_id
    node_id += 1
    workflow[str(encode_neg_id)] = {
        "inputs": {"text": cfg["negative"], "clip": last_clip},
        "class_type": "CLIPTextEncode",
    }

    # Generate polar bear frames.
    # NOTE: ControlNet OpenPose is intentionally not wired here because it requires
    # a pose reference image. We rely on consistent prompts and per-direction seeds
    # for frame consistency. ControlNet Canny can be added later for shape guidance.
    node_id = 10
    for direction in ["north", "east", "south", "west"]:
        base_seed = {"north": 1000, "east": 2000, "south": 3000, "west": 4000}[direction]
        for frame_idx, pose in enumerate(WALK_POSES):
            seed = base_seed + frame_idx * 7
            key = f"polar_bear_{direction}_f{frame_idx + 1}"
            prompt_text = prompt_for_frame(direction, pose)

            # Each frame needs its own positive prompt encoder.
            encode_pos_id = node_id
            node_id += 1
            workflow[str(encode_pos_id)] = {
                "inputs": {"text": prompt_text, "clip": last_clip},
                "class_type": "CLIPTextEncode",
            }

            sampler_id = str(node_id)
            decode_id = str(node_id + 1)
            save_id = str(node_id + 2)
            positive_ref = [str(encode_pos_id), 0]

            workflow[sampler_id] = {
                "inputs": {
                    "seed": seed,
                    "steps": cfg["steps"],
                    "cfg": cfg["cfg"],
                    "sampler_name": cfg["sampler"],
                    "scheduler": cfg["scheduler"],
                    "denoise": 1,
                    "model": last_model,
                    "positive": positive_ref,
                    "negative": [str(encode_neg_id), 0],
                    "latent_image": [str(latent_id), 0],
                },
                "class_type": "KSampler",
            }
            workflow[decode_id] = {
                "inputs": {"samples": [sampler_id, 0], "vae": ["1", 2]},
                "class_type": "VAEDecode",
            }
            workflow[save_id] = {
                "inputs": {"filename_prefix": f"{key}_unique_{direction}_{frame_idx}", "images": [decode_id, 0]},
                "class_type": "SaveImage",
            }

            node_id += 10

    # Generate tile textures.
    # Start tile IDs well above the polar bear section to avoid collisions.
    tile_base_id = ((node_id + 99) // 100) * 100
    tile_node_id = tile_base_id
    for tile_name, tile_prompt in TILE_DESCRIPTIONS.items():
        encode_pos_id = node_id
        node_id += 1
        workflow[str(encode_pos_id)] = {
            "inputs": {"text": tile_prompt, "clip": last_clip},
            "class_type": "CLIPTextEncode",
        }

        sampler_id = str(tile_node_id)
        decode_id = str(tile_node_id + 1)
        save_id = str(tile_node_id + 2)

        workflow[sampler_id] = {
            "inputs": {
                "seed": 9000 + hash(tile_name) % 1000,
                "steps": cfg["steps"],
                "cfg": cfg["cfg"],
                "sampler_name": cfg["sampler"],
                "scheduler": cfg["scheduler"],
                "denoise": 1,
                "model": last_model,
                "positive": [str(encode_pos_id), 0],
                "negative": [str(encode_neg_id), 0],
                "latent_image": [str(latent_id), 0],
            },
            "class_type": "KSampler",
        }
        workflow[decode_id] = {
            "inputs": {"samples": [sampler_id, 0], "vae": ["1", 2]},
            "class_type": "VAEDecode",
        }
        workflow[save_id] = {
            "inputs": {"filename_prefix": f"tile_{tile_name}_unique_{tile_node_id}", "images": [decode_id, 0]},
            "class_type": "SaveImage",
        }

        tile_node_id += 10

    return workflow


def build_turbo_workflow(controlnet_available: bool) -> dict:
    cfg = MODES["turbo"]
    workflow: dict = {}

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


def build_workflow(mode: str, controlnet_available: bool, lora_name: str | None = None) -> dict:
    if mode == "sd15":
        return build_sd15_workflow(controlnet_available, lora_name)
    return build_turbo_workflow(controlnet_available)


def queue_prompt(workflow: dict) -> str:
    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_prompt(prompt_id: str, timeout: int = 3600) -> dict:
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
            # Extract prefix from filename like polar_bear_north_f1_unique_north_1_00001_.png
            # The unique suffix guarantees one file per save node.
            parts = filename.split("_")
            if "unique" in parts:
                unique_idx = parts.index("unique")
                prefix = "_".join(parts[:unique_idx])
            else:
                prefix = filename.rsplit("_", 2)[0]
            downloaded[prefix] = out_path
            print(f"saved: {out_path} (prefix={prefix})")
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
        "--mode", choices=["sd15", "turbo"], default="sd15",
        help="Model stack to use (default: sd15 for 8GB VRAM)"
    )
    parser.add_argument(
        "--lora", default=None,
        help="Optional LoRA filename from ComfyUI/models/loras/"
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Inspecting ComfyUI server at {COMFYUI_URL}...")
    server_info = inspect_server()
    print(json.dumps(server_info, indent=2))

    cfg = MODES[args.mode]
    if args.mode == "sd15":
        if cfg["checkpoint"] not in server_info.get("checkpoints", []):
            print(f"ERROR: missing checkpoint {cfg['checkpoint']}", file=sys.stderr)
            sys.exit(1)
    else:
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
    if args.lora and args.lora not in server_info.get("loras", []):
        print(f"WARNING: LoRA '{args.lora}' not found; continuing without it", file=sys.stderr)
        args.lora = None

    workflow = build_workflow(args.mode, controlnet_available, args.lora)
    workflow_path = OUTPUT_DIR / f"workflow_polar_assets_v3_{args.mode}.json"
    workflow_path.write_text(json.dumps(workflow, indent=2))
    print(f"workflow written to {workflow_path}")

    print("queueing prompt...")
    prompt_id = queue_prompt(workflow)
    print(f"prompt_id: {prompt_id}")

    print("waiting for completion (this may take 10-30 minutes on 8GB VRAM)...")
    history = wait_for_prompt(prompt_id)
    status = history.get("status", {})
    if status.get("status_str") == "error":
        print(f"ERROR: workflow failed: {status}", file=sys.stderr)
        sys.exit(1)
    print("done")

    download_outputs(history)
    print("\nnext: run postprocess_assets.py --v3 to assemble the final spritesheet")


if __name__ == "__main__":
    main()
