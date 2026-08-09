#!/usr/bin/env python3
"""Repair the existing flat-vector polar bear references.

The white-fringe decontamination pass over-aggressively punched holes in the
back-facing polar bear's white head. This script:

1. Hard-binarises alpha on all four references so fringe pixels are either
   fully opaque or fully transparent.
2. Reclaims the transparent-but-white pixels inside the up reference's head
   region so the checkerboard background no longer shows through.
3. Rebuilds the 4x4 spritesheet and hard-binarises its alpha.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comfy_generate import _hard_alpha_cut

ROOT = Path(__file__).resolve().parents[1]
CHARS = ROOT / "public/assets/generated/characters"


def repair(path: Path, head_box: tuple[int, int, int, int] | None = None) -> Image.Image:
    """Hard-binarise alpha; optionally recover white pixels inside a head box."""
    img = Image.open(path).convert("RGBA")
    arr = np.array(img).astype(np.float32)

    if head_box is not None:
        x1, y1, x2, y2 = head_box
        rgb = arr[:, :, :3]
        alpha = arr[:, :, 3]
        max_rgb = rgb.max(axis=2)
        min_rgb = rgb.min(axis=2)
        saturation = np.where(max_rgb > 0, (max_rgb - min_rgb) / max_rgb, 0)

        mask = np.zeros(alpha.shape, bool)
        mask[y1:y2, x1:x2] = True
        recover = (
            mask
            & (alpha == 0)
            & (max_rgb > 230)
            & (saturation < 0.2)
        )
        arr[recover, 3] = 255

    return _hard_alpha_cut(Image.fromarray(arr.astype(np.uint8)))


def build_sheet(frames: dict[str, Image.Image]) -> Image.Image:
    cell = 128
    sheet = Image.new("RGBA", (cell * 4, cell * 4), (255, 255, 255, 0))
    order = ["up", "right", "down", "left"]
    for row, name in enumerate(order):
        img = frames[name]
        scale = cell / max(img.size)
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        frame = Image.new("RGBA", (cell, cell), (255, 255, 255, 0))
        x = (cell - img.width) // 2
        y = (cell - img.height) // 2
        frame.paste(img, (x, y), img)
        for col in range(4):
            sheet.paste(frame, (col * cell, row * cell), frame)
    # LANCZOS reintroduces soft edges; binarise the final flat sheet.
    return _hard_alpha_cut(sheet)


refs = {
    "down": CHARS / "bear-reference-down.png",
    "left": CHARS / "bear-reference-left.png",
    "right": CHARS / "bear-reference-right.png",
    "up": CHARS / "bear-reference-up.png",
}

# Head bounding box for the back-facing reference in the 512x512 canvas.
head_box_up = (180, 20, 340, 130)

repaired: dict[str, Image.Image] = {}
for name, path in refs.items():
    print(f"repairing {name}...")
    box = head_box_up if name == "up" else None
    fixed = repair(path, head_box=box)
    fixed.save(path)
    repaired[name] = fixed

print("rebuilding polar-bear.png...")
sheet = build_sheet(repaired)
sheet_path = CHARS / "polar-bear.png"
sheet.save(sheet_path)
print(f"saved {sheet_path}")
