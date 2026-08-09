#!/usr/bin/env python3
"""
Generate an extended placeholder polar bear spritesheet for animation review.

Frame size: 128x128
Sheet: 512x1024
Rows:
  0: walk north      (4 frames)
  1: walk east       (4 frames)
  2: walk south      (4 frames)
  3: walk west       (4 frames)
  4: swim             (4 frames)
  5: attack / swipe  (4 frames)
  6: push / interact (4 frames)
  7: idle-breathe     (4 frames)

Placeholder frames are simple geometric shapes; the real ComfyUI pass will
replace this with detailed 128x128 frames.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public/assets/characters/polar-bear.png"
FRAME = 128
COLS = 4
ROWS = 8

def draw_ellipse(draw, bbox, color):
    draw.ellipse(bbox, fill=color)

def draw_body(draw, cx, cy, direction, bob):
    is_side = direction in ("east", "west")
    is_back = direction == "north"

    body_w = 52 if is_side else 56
    body_h = 64 if is_side else 60
    body_top = cy - body_h // 2 + bob
    draw_ellipse(draw, [cx - body_w // 2, body_top, cx + body_w // 2, body_top + body_h], "#ffffff")

    head_r = 22
    head_y = body_top - 12
    draw_ellipse(draw, [cx - head_r, head_y - head_r, cx + head_r, head_y + head_r], "#ffffff")

    ear_r = 8
    draw_ellipse(draw, [cx - head_r - 2, head_y - head_r - 2, cx - head_r + 10, head_y - head_r + 14], "#ffffff")
    draw_ellipse(draw, [cx + head_r - 10, head_y - head_r - 2, cx + head_r + 2, head_y - head_r + 14], "#ffffff")

    if not is_back:
        if is_side:
            side = 1 if direction == "east" else -1
            eye_x = cx + side * 10
            eye_y = head_y - 4
            draw_ellipse(draw, [eye_x - 4, eye_y - 4, eye_x + 4, eye_y + 4], "#111111")
            nose_x = cx + side * 24
            nose_y = head_y + 8
            draw_ellipse(draw, [nose_x - 4, nose_y - 4, nose_x + 4, nose_y + 4], "#111111")
        else:
            draw_ellipse(draw, [cx - 12, head_y - 4, cx - 4, head_y + 4], "#111111")
            draw_ellipse(draw, [cx + 4, head_y - 4, cx + 12, head_y + 4], "#111111")
            draw_ellipse(draw, [cx - 4, head_y + 8, cx + 4, head_y + 16], "#111111")

    leg_w = 12
    leg_h = 20
    if is_side:
        offsets = [(-16, 0), (16, 0)]
    else:
        offsets = [(-20, -4), (-20, 12), (20, -4), (20, 12)]

    for i, (ox, oy) in enumerate(offsets):
        lx = cx + ox
        ly = body_top + body_h - 4 + (oy // 2)
        draw_ellipse(draw, [lx - leg_w // 2, ly, lx + leg_w // 2, ly + leg_h], "#f0f0f0")

def draw_direction_walk(draw, col, row, frame_idx):
    x0 = col * FRAME
    y0 = row * FRAME
    cx = x0 + FRAME // 2
    cy = y0 + FRAME // 2
    direction = ["north", "east", "south", "west"][row]
    bobs = [0, -4, 0, -4]
    draw_body(draw, cx, cy, direction, bobs[frame_idx])

def draw_swim(draw, col, row, frame_idx):
    x0 = col * FRAME
    y0 = row * FRAME
    cx = x0 + FRAME // 2
    cy = y0 + FRAME // 2
    bob = [0, -6, -2, -6][frame_idx]
    # Submerged body.
    draw_ellipse(draw, [cx - 30, cy + 20 + bob, cx + 30, cy + 56 + bob], "#ffffff")
    # Head above water.
    draw_ellipse(draw, [cx - 22, cy - 10 + bob, cx + 22, cy + 30 + bob], "#ffffff")
    draw_ellipse(draw, [cx - 6, cy + 4 + bob, cx + 6, cy + 16 + bob], "#111111")
    # Paws paddling.
    paw_y = cy + 36 + bob
    offset = [-18, -6, 6, 18][frame_idx]
    draw_ellipse(draw, [cx + offset - 8, paw_y, cx + offset + 8, paw_y + 12], "#f0f0f0")

def draw_attack(draw, col, row, frame_idx):
    x0 = col * FRAME
    y0 = row * FRAME
    cx = x0 + FRAME // 2
    cy = y0 + FRAME // 2
    draw_body(draw, cx, cy, "south", 0)
    # Swipe arc.
    swipe_x = cx + [-30, -10, 30, 40][frame_idx]
    swipe_y = cy + [-20, -40, -30, 10][frame_idx]
    draw_ellipse(draw, [swipe_x - 10, swipe_y - 10, swipe_x + 10, swipe_y + 10], "#ffffff")
    draw_ellipse(draw, [swipe_x - 4, swipe_y - 4, swipe_x + 4, swipe_y + 4], "#cceeff")

def draw_push(draw, col, row, frame_idx):
    x0 = col * FRAME
    y0 = row * FRAME
    cx = x0 + FRAME // 2
    cy = y0 + FRAME // 2
    lean = [0, 6, 12, 6][frame_idx]
    draw_body(draw, cx + lean, cy, "south", 0)
    # Outstretched paws.
    draw_ellipse(draw, [cx + 20 + lean, cy + 10, cx + 48 + lean, cy + 26], "#ffffff")
    draw_ellipse(draw, [cx - 48 + lean, cy + 10, cx - 20 + lean, cy + 26], "#ffffff")

def draw_idle_breathe(draw, col, row, frame_idx):
    x0 = col * FRAME
    y0 = row * FRAME
    cx = x0 + FRAME // 2
    cy = y0 + FRAME // 2
    bob = [0, -2, -3, -2][frame_idx]
    scale_w = [56, 58, 58, 56][frame_idx]
    body_h = 60
    body_top = cy - body_h // 2 + bob
    draw_ellipse(draw, [cx - scale_w // 2, body_top, cx + scale_w // 2, body_top + body_h], "#ffffff")
    # Head.
    head_r = 22
    head_y = body_top - 12
    draw_ellipse(draw, [cx - head_r, head_y - head_r, cx + head_r, head_y + head_r], "#ffffff")
    draw_ellipse(draw, [cx - 12, head_y - 4, cx - 4, head_y + 4], "#111111")
    draw_ellipse(draw, [cx + 4, head_y - 4, cx + 12, head_y + 4], "#111111")
    draw_ellipse(draw, [cx - 4, head_y + 8, cx + 4, head_y + 16], "#111111")

ROW_DRAWERS = [
    draw_direction_walk,
    draw_direction_walk,
    draw_direction_walk,
    draw_direction_walk,
    draw_swim,
    draw_attack,
    draw_push,
    draw_idle_breathe,
]

def main():
    img = Image.new("RGBA", (FRAME * COLS, FRAME * ROWS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for row in range(ROWS):
        for col in range(COLS):
            ROW_DRAWERS[row](draw, col, row, col)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print(f"saved {OUT} ({img.width}x{img.height})")

if __name__ == "__main__":
    main()
