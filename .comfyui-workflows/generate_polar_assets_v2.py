#!/usr/bin/env python3
"""
Generate Polar Adventures game assets via ComfyUI.

Optimized for an RTX 4060 8GB setup. Supports two modes:
  1. "turbo"  - uses your existing z-image-turbo AuraFlow checkpoint.
                Heaviest option; works if it already fits in 8GB for you.
  2. "sd15"   - uses an SD 1.5 checkpoint. Recommended for 8GB cards because
                the base model is ~4GB, leaving room for LoRAs, ControlNet,
                and background-removal nodes.

For the easiest high-quality results on 8GB, install the SD 1.5 stack:
  - Checkpoint: v1-5-pruned-emaonly.safetensors  (ComfyUI/models/checkpoints/)
  - LoRA:       isometric/pixel-art style LoRA  (ComfyUI/models/loras/)
  - ControlNet: control_v11p_sd15_openpose.pth   (ComfyUI/models/controlnet/)
  - Nodes:      ComfyUI-layerdiffuse (transparent PNGs for SD1.5)

Then run:
    python3 .comfyui-workflows/generate_polar_assets_v2.py --mode sd15

If you only have z-image-turbo working, run:
    python3 .comfyui-workflows/generate_polar_assets_v2.py --mode turbo
"""
import argparse
import json
import requests
import sys
import time
from pathlib import Path

COMFYUI_URL = "http://note:8188"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets-src"

# We ask ComfyUI for a bright lime background so post-processing can key it out
# reliably. Lime green (#00FF00) is very unlikely to appear in arctic assets.
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
    "sd15": {
        "checkpoint": "v1-5-pruned-emaonly.safetensors",
        "vae": "ae.safetensors",
        "steps": 20,
        "cfg": 7.0,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "latent": "EmptyLatentImage",
        "width": 512,
        "height": 512,
        "scale_to": 256,
    },
    "layerdiffuse": {
        "checkpoint": "v1-5-pruned-emaonly.safetensors",
        "steps": 25,
        "cfg": 7.0,
        "sampler": "dpmpp_2m",
        "scheduler": "karras",
        "latent": "EmptyLatentImage",
        "width": 512,
        "height": 512,
        "scale_to": 256,
    },
}


def prompt_for_tile(name: str) -> str:
    """Return a prompt tuned for flat isometric floor tiles."""
    descriptions = {
        "snow": "fresh powder snow, subtle sparkles, soft drifts",
        "ice": "smooth frozen lake ice, pale blue, glossy highlights",
        "ice_cracks": "frozen lake ice with dark cracks, pale blue and white",
    }
    return (
        f"flat isometric floor tile texture, {descriptions[name]}, "
        "game asset, top-down view, no 3D sides, no thickness, "
        "soft ambient lighting, clean diamond edges, centered, "
        f"{CHROMA_BG}, high quality"
    )


def prompt_for_bear(direction: str, mode: str = "sd15") -> str:
    """Return a prompt tuned for a consistent polar bear game sprite."""
    views = {
        "north": "back view, facing away from camera",
        "east": "right side view, facing right",
        "south": "front view, facing toward camera",
        "west": "left side view, facing left",
    }
    bg = "transparent background, isolated character" if mode == "layerdiffuse" else CHROMA_BG
    return (
        "cute polar bear character, chibi proportions, "
        f"{views[direction]}, "
        "full body visible, standing pose, "
        "white fluffy fur, small black eyes and nose, "
        "game sprite, clean vector-like style, soft shading, "
        f"{bg}, centered, high quality"
    )


def _add_sd15_chain(
    workflow: dict,
    start_id: int,
    prompt_text: str,
    cfg: dict,
    model_ref: list,
    latent_ref: list,
    vae_ref: list,
    filename_prefix: str,
    use_layerdiffuse: bool = False,
) -> int:
    """Add one sd15/layerdiffuse generation chain and return the next free node id."""
    encode_id = str(start_id)
    negative_id = str(start_id + 1)
    sampler_id = str(start_id + 2)
    decode_id = str(start_id + 3)

    workflow[encode_id] = {
        "inputs": {"text": prompt_text, "clip": ["1", 1]},
        "class_type": "CLIPTextEncode",
    }
    workflow[negative_id] = {
        "inputs": {
            "text": "blurry, low quality, watermark, signature, text, cropped, worst quality",
            "clip": ["1", 1],
        },
        "class_type": "CLIPTextEncode",
    }
    workflow[sampler_id] = {
        "inputs": {
            "seed": 0,
            "steps": cfg["steps"],
            "cfg": cfg["cfg"],
            "sampler_name": cfg["sampler"],
            "scheduler": cfg["scheduler"],
            "denoise": 1,
            "model": model_ref,
            "positive": [encode_id, 0],
            "negative": [negative_id, 0],
            "latent_image": latent_ref,
        },
        "class_type": "KSampler",
    }
    workflow[decode_id] = {
        "inputs": {"samples": [sampler_id, 0], "vae": vae_ref},
        "class_type": "VAEDecode",
    }

    image_ref = [decode_id, 0]
    next_id = start_id + 4

    if use_layerdiffuse:
        rgba_id = str(start_id + 4)
        workflow[rgba_id] = {
            "inputs": {
                "samples": [sampler_id, 0],
                "images": [decode_id, 0],
                "sd_version": "SD15",
                "sub_batch_size": 16,
            },
            "class_type": "LayeredDiffusionDecodeRGBA",
        }
        image_ref = [rgba_id, 0]
        next_id = start_id + 5

    scale_id = str(next_id)
    save_id = str(next_id + 1)
    workflow[scale_id] = {
        "inputs": {
            "image": image_ref,
            "upscale_method": "lanczos",
            "width": cfg["scale_to"],
            "height": cfg["scale_to"],
            "crop": "center",
        },
        "class_type": "ImageScale",
    }
    workflow[save_id] = {
        "inputs": {
            "filename_prefix": filename_prefix,
            "images": [scale_id, 0],
        },
        "class_type": "SaveImage",
    }

    return next_id + 2


def build_workflow(mode: str) -> dict:
    cfg = MODES[mode]
    workflow: dict = {}

    if mode == "turbo":
        workflow["1"] = {
            "inputs": {
                "clip_name": cfg["clip"],
                "type": cfg["clip_type"],
                "device": "default",
            },
            "class_type": "CLIPLoader",
        }
        workflow["2"] = {
            "inputs": {"vae_name": cfg["vae"]},
            "class_type": "VAELoader",
        }
        workflow["3"] = {
            "inputs": {
                "unet_name": cfg["unet"],
                "weight_dtype": "default",
            },
            "class_type": "UNETLoader",
        }
        workflow["4"] = {
            "inputs": {"shift": cfg["model_sampling_shift"], "model": ["3", 0]},
            "class_type": cfg["model_sampling"],
        }
        workflow["5"] = {
            "inputs": {
                "width": cfg["width"],
                "height": cfg["height"],
                "batch_size": 1,
            },
            "class_type": cfg["latent"],
        }
    elif mode in ("sd15", "layerdiffuse"):
        workflow["1"] = {
            "inputs": {"ckpt_name": cfg["checkpoint"]},
            "class_type": "CheckpointLoaderSimple",
        }
        if mode == "sd15":
            workflow["2"] = {
                "inputs": {"vae_name": cfg["vae"]},
                "class_type": "VAELoader",
            }
        else:
            workflow["2"] = {
                "inputs": {
                    "model": ["1", 0],
                    "config": "SD1.x, Attention Injection, attn_sharing",
                    "weight": 1.0,
                },
                "class_type": "LayeredDiffusionApply",
            }
        workflow["3"] = {
            "inputs": {
                "width": cfg["width"],
                "height": cfg["height"],
                "batch_size": 1,
            },
            "class_type": cfg["latent"],
        }

    prompts: dict[str, str] = {}
    for direction in ["north", "east", "south", "west"]:
        prompts[f"polar_bear_{direction}"] = prompt_for_bear(direction, mode=mode)
    for tile in ["snow", "ice", "ice_cracks"]:
        prompts[f"tile_{tile}"] = prompt_for_tile(tile)

    node_id = 10
    for key, prompt_text in prompts.items():
        if mode == "turbo":
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
                    "seed": 0,
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
                "inputs": {
                    "filename_prefix": key,
                    "images": [scale_id, 0],
                },
                "class_type": "SaveImage",
            }
            node_id += 10
        elif mode == "sd15":
            node_id = _add_sd15_chain(
                workflow,
                node_id,
                prompt_text,
                cfg,
                model_ref=["1", 0],
                latent_ref=["3", 0],
                vae_ref=["2", 0],
                filename_prefix=key,
                use_layerdiffuse=False,
            )
        else:  # layerdiffuse
            use_layerdiffuse = key.startswith("polar_bear_")
            # For layerdiffuse bears we use the checkpoint's built-in VAE. Tiles
            # also use it so no external VAE loader is needed.
            node_id = _add_sd15_chain(
                workflow,
                node_id,
                prompt_text,
                cfg,
                model_ref=["2", 0],
                latent_ref=["3", 0],
                vae_ref=["1", 2],
                filename_prefix=key,
                use_layerdiffuse=use_layerdiffuse,
            )

    return workflow


def queue_prompt(workflow: dict) -> str:
    resp = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    resp.raise_for_status()
    return resp.json()["prompt_id"]


def wait_for_prompt(prompt_id: str, timeout: int = 900) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        resp.raise_for_status()
        data = resp.json()
        if data:
            return data[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Prompt {prompt_id} did not complete within {timeout}s")


def download_outputs(history: dict) -> None:
    outputs = history["outputs"]
    for node_id, node_outputs in outputs.items():
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
            print(f"saved: {out_path}")


def inspect_server() -> dict:
    """Probe ComfyUI for available checkpoints/UNETs via object_info."""
    info: dict = {}
    try:
        resp = requests.get(f"{COMFYUI_URL}/object_info/CheckpointLoaderSimple")
        resp.raise_for_status()
        data = resp.json()
        info["checkpoints"] = data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    except Exception as e:
        info["checkpoints_error"] = str(e)

    try:
        resp = requests.get(f"{COMFYUI_URL}/object_info/UNETLoader")
        resp.raise_for_status()
        data = resp.json()
        info["unets"] = data["UNETLoader"]["input"]["required"]["unet_name"][0]
    except Exception as e:
        info["unets_error"] = str(e)

    try:
        resp = requests.get(f"{COMFYUI_URL}/object_info/CLIPLoader")
        resp.raise_for_status()
        data = resp.json()
        info["clips"] = data["CLIPLoader"]["input"]["required"]["clip_name"][0]
    except Exception as e:
        info["clips_error"] = str(e)

    try:
        resp = requests.get(f"{COMFYUI_URL}/object_info/VAELoader")
        resp.raise_for_status()
        data = resp.json()
        info["vaes"] = data["VAELoader"]["input"]["required"]["vae_name"][0]
    except Exception as e:
        info["vaes_error"] = str(e)

    for endpoint, key in [
        ("loras", "loras"),
        ("controlnet", "controlnet"),
    ]:
        try:
            resp = requests.get(f"{COMFYUI_URL}/models/{endpoint}")
            resp.raise_for_status()
            info[key] = resp.json()
        except Exception as e:
            info[f"{key}_error"] = str(e)
    return info


def main():
    parser = argparse.ArgumentParser(
        description="Generate Polar Adventures assets via ComfyUI"
    )
    parser.add_argument(
        "--mode",
        choices=["turbo", "sd15", "layerdiffuse"],
        default="turbo",
        help="Which model stack to use (default: turbo)",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Inspecting ComfyUI server at {COMFYUI_URL}...")
    server_info = inspect_server()
    print(json.dumps(server_info, indent=2))

    cfg = MODES[args.mode]
    if args.mode == "turbo":
        required = [cfg["unet"], cfg["clip"], cfg["vae"]]
        available = (
            server_info.get("unets", [])
            + server_info.get("clips", [])
            + server_info.get("vaes", [])
        )
    elif args.mode == "sd15":
        required = [cfg["checkpoint"], cfg["vae"]]
        available = server_info.get("checkpoints", []) + server_info.get("vaes", [])
    else:  # layerdiffuse
        required = [cfg["checkpoint"]]
        available = server_info.get("checkpoints", [])

    missing = [r for r in required if r not in available]
    if missing:
        print(
            f"ERROR: missing required models for --mode {args.mode}: {missing}",
            file=sys.stderr,
        )
        if args.mode == "sd15":
            print(
                "\nRecommended 8GB-friendly setup:\n"
                "  1. Download v1-5-pruned-emaonly.safetensors (~4GB)\n"
                "     to ComfyUI/models/checkpoints/\n"
                "  2. (Optional) Install ComfyUI-layerdiffuse for native transparent PNGs\n"
                "  3. (Optional) Add isometric/pixel-art LoRAs to ComfyUI/models/loras/\n"
                "  4. Restart ComfyUI and rerun this script\n",
                file=sys.stderr,
            )
        else:
            print(
                "Install them in ComfyUI/models/... and restart ComfyUI.",
                file=sys.stderr,
            )
        sys.exit(1)

    workflow = build_workflow(args.mode)
    workflow_path = OUTPUT_DIR / f"workflow_polar_assets_v2_{args.mode}.json"
    workflow_path.write_text(json.dumps(workflow, indent=2))
    print(f"workflow written to {workflow_path}")

    print("queueing prompt...")
    prompt_id = queue_prompt(workflow)
    print(f"prompt_id: {prompt_id}")

    print("waiting for completion (this may take a few minutes on 8GB VRAM)...")
    history = wait_for_prompt(prompt_id)
    print("done")

    download_outputs(history)
    print("\nnext step: run postprocess_assets.py to convert outputs into public/assets/")


if __name__ == "__main__":
    main()
