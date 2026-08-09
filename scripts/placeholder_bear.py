#!/usr/bin/env python3
"""
Generate a clean placeholder polar bear spritesheet for layout review.

Each cell is 64x64. The sheet is 4 columns (frames) x 4 rows (directions):
  row 0: north (back)
  row 1: east (right side)
  row 2: south (front)
  row 3: west (left side)

Walk frames are identical except for a slight body bob so movement reads as
animated even though the placeholder art is simple.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public/assets/characters/polar-bear.png"
FRAME = 64

def draw_ellipse(draw, bbox, color):
    draw.ellipse(bbox, fill=color)

def draw_direction(draw, col, row, frame_idx):
    x0 = col * FRAME
    y0 = row * FRAME
    cx = x0 + FRAME // 2
    cy = y0 + FRAME // 2

    # Walk bob offsets.
    bobs = [0, -2, 0, -2]
    bob = bobs[frame_idx]

    direction = ["north", "east", "south", "west"][row]
    is_side = direction in ("east", "west")
    is_back = direction == "north"

    # Body (white oval).
    body_w = 26 if is_side else 28
    body_h = 32 if is_side else 30
    body_top = cy - body_h // 2 + bob
    draw_ellipse(draw, [cx - body_w // 2, body_top, cx + body_w // 2, body_top + body_h], "#ffffff")

    # Head.
    head_r = 11
    head_y = body_top - 6
    draw_ellipse(draw, [cx - head_r, head_y - head_r, cx + head_r, head_y + head_r], "#ffffff")

    # Ears.
    ear_r = 4
    draw_ellipse(draw, [cx - head_r - 1, head_y - head_r - 1, cx - head_r + 5, head_y - head_r + 7], "#ffffff")
    draw_ellipse(draw, [cx + head_r - 5, head_y - head_r - 1, cx + head_r + 1, head_y - head_r + 7], "#ffffff")

    if not is_back:
        # Eyes and nose (front/side).
        if is_side:
            # Single eye visible on side views.
            side = 1 if direction == "east" else -1
            eye_x = cx + side * 5
            eye_y = head_y - 2
            draw_ellipse(draw, [eye_x - 2, eye_y - 2, eye_x + 2, eye_y + 2], "#111111")
            nose_x = cx + side * 12
            nose_y = head_y + 4
            draw_ellipse(draw, [nose_x - 2, nose_y - 2, nose_x + 2, nose_y + 2], "#111111")
        else:
            # Front view: two eyes + nose.
            draw_ellipse(draw, [cx - 6, head_y - 2, cx - 2, head_y + 2], "#111111")
            draw_ellipse(draw, [cx + 2, head_y - 2, cx + 6, head_y + 2], "#111111")
            draw_ellipse(draw, [cx - 2, head_y + 4, cx + 2, head_y + 8], "#111111")

    # Legs.
    leg_w = 6
    leg_h = 10
    if is_side:
        # Two legs visible, one behind one front.
        side = 1 if direction == "east" else -1
        offsets = [(-8, 0), (8, 0)]
    else:
        offsets = [(-10, -2), (-10, 6), (10, -2), (10, 6)]

    for i, (ox, oy) in enumerate(offsets):
        lx = cx + ox
        ly = body_top + body_h - 2 + (bobs[(frame_idx + i) % 4] if not is_back else 0)
        draw_ellipse(draw, [lx - leg_w // 2, ly, lx + leg_w // 2, ly + leg_h], "#f0f0f0")


def main():
    img = Image.new("RGBA", (FRAME * 4, FRAME * 4), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for row in range(4):
        for col in range(4):
            draw_direction(draw, col, row, col)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
