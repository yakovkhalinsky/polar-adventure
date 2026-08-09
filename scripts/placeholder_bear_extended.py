#!/usr/bin/env python3
"""
Generate an extended placeholder polar bear spritesheet for animation review.

Frame size: 128x128
Sheet: 512x1024
Rows:
  0: walk up       (4 frames)
  1: walk right    (4 frames)
  2: walk down     (4 frames)
  3: walk left     (4 frames)
  4: swim          (4 frames)
  5: attack        (4 frames)
  6: push          (4 frames)
  7: idle-breathe  (4 frames, ping-pong)

Art direction: adult anthropomorphic polar bear, upright humanoid posture,
wearing a blue hoodie and dark jeans. No gloves, no headband. Friendly smile.
"""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public/assets/characters/polar-bear.png"
FRAME = 128
COLS = 4
ROWS = 8

# Palette
FUR = "#f7f7f7"
FUR_SHADOW = "#d9e0e6"
SNOUT = "#ffffff"
NOSE = "#1a1a1a"
EYE = "#1a1a1a"
HOODIE = "#4a7fc1"
HOODIE_DARK = "#3a6299"
HOODIE_LIGHT = "#6a9fd9"
JEANS = "#2a3a5e"
JEANS_DARK = "#1f2d4a"
Paws = "#f7f7f7"
Paws_SHADOW = "#d9e0e6"


def draw_ellipse(draw, bbox, color):
    draw.ellipse(bbox, fill=color)


def draw_round_rect(draw, bbox, color, radius=8):
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, radius=radius, fill=color)


def cxcy(col, row):
    return col * FRAME + FRAME // 2, row * FRAME + FRAME // 2


def draw_head(draw, cx, cy, direction, smile=True, eyes_open=True):
    """Draw a friendly adult bear head."""
    is_side = direction in ("right", "left")
    is_back = direction == "up"

    # Head shape: slightly tall oval.
    head_w = 34 if is_side else 36
    head_h = 40
    head_top = cy - head_h // 2 - 26
    draw_ellipse(draw, [cx - head_w // 2, head_top, cx + head_w // 2, head_top + head_h], FUR)

    # Ears on top.
    ear_r = 9
    ear_y = head_top + 6
    draw_ellipse(draw, [cx - head_w // 2 - 2, ear_y - ear_r, cx - head_w // 2 + 12, ear_y + ear_r], FUR)
    draw_ellipse(draw, [cx + head_w // 2 - 12, ear_y - ear_r, cx + head_w // 2 + 2, ear_y + ear_r], FUR)

    if is_back:
        return

    if is_side:
        side = 1 if direction == "right" else -1
        # Snout sticking forward.
        snout_x = cx + side * 16
        snout_y = head_top + 18
        draw_ellipse(draw, [snout_x - 10, snout_y - 8, snout_x + 10, snout_y + 10], SNOUT)
        # Nose at tip.
        draw_ellipse(draw, [snout_x + side * 5 - 4, snout_y - 4, snout_x + side * 5 + 4, snout_y + 4], NOSE)
        # Eye.
        eye_x = cx + side * 4
        eye_y = head_top + 12
        if eyes_open:
            draw_ellipse(draw, [eye_x - 3, eye_y - 3, eye_x + 3, eye_y + 3], EYE)
        else:
            draw.line([(eye_x - 4, eye_y), (eye_x + 4, eye_y)], fill=EYE, width=2)
        # Smile.
        if smile:
            smile_y = snout_y + 4
            draw.arc([snout_x - 8, smile_y - 4, snout_x + 8, smile_y + 8], 180 if side == 1 else 0, 0 if side == 1 else 180, fill=EYE, width=2)
    else:
        # Front face.
        snout_y = head_top + 24
        draw_ellipse(draw, [cx - 12, snout_y - 8, cx + 12, snout_y + 10], SNOUT)
        # Eyes.
        eye_y = head_top + 14
        if eyes_open:
            draw_ellipse(draw, [cx - 13, eye_y - 3, cx - 5, eye_y + 3], EYE)
            draw_ellipse(draw, [cx + 5, eye_y - 3, cx + 13, eye_y + 3], EYE)
        else:
            draw.line([(cx - 13, eye_y), (cx - 5, eye_y)], fill=EYE, width=2)
            draw.line([(cx + 5, eye_y), (cx + 13, eye_y)], fill=EYE, width=2)
        # Nose.
        draw_ellipse(draw, [cx - 5, snout_y + 2, cx + 5, snout_y + 10], NOSE)
        # Smile.
        if smile:
            smile_y = snout_y + 10
            draw.arc([cx - 10, smile_y - 4, cx + 10, smile_y + 8], 0, 180, fill=EYE, width=2)


def draw_hoodie_body(draw, cx, cy, direction):
    """Torso in a hoodie, slightly boxy."""
    is_side = direction in ("right", "left")
    body_w = 38 if is_side else 42
    body_h = 52
    body_top = cy - 4
    draw_round_rect(draw, [cx - body_w // 2, body_top, cx + body_w // 2, body_top + body_h], HOODIE, radius=10)

    # Hood rim / zipper line.
    if not is_side:
        draw.line([(cx, body_top + 8), (cx, body_top + body_h - 8)], fill=HOODIE_DARK, width=2)
        # Pocket.
        draw_round_rect(draw, [cx - 12, body_top + 28, cx + 12, body_top + 42], HOODIE_DARK, radius=4)
    else:
        # Side hoodie seam and pocket hint.
        side = 1 if direction == "right" else -1
        draw.line([(cx, body_top + 8), (cx, body_top + body_h - 8)], fill=HOODIE_DARK, width=2)
        draw_ellipse(draw, [cx + side * 6 - 6, body_top + 28, cx + side * 6 + 6, body_top + 40], HOODIE_DARK)

    # Hood opening around neck.
    neck_y = body_top + 6
    draw_ellipse(draw, [cx - 12, neck_y - 4, cx + 12, neck_y + 8], FUR)


def draw_jeans_legs(draw, cx, cy, direction, stride=0):
    """Two legs in jeans."""
    is_side = direction in ("right", "left")
    body_top = cy - 4
    leg_top = body_top + 46
    leg_w = 12
    leg_h = 34

    if is_side:
        # One visible leg with a hint of the back leg.
        side = 1 if direction == "right" else -1
        front_x = cx + side * 4 + stride * 6
        draw_round_rect(draw, [front_x - leg_w // 2, leg_top, front_x + leg_w // 2, leg_top + leg_h], JEANS, radius=4)
        # Back leg slightly darker.
        back_x = cx - side * 4 - stride * 3
        draw_round_rect(draw, [back_x - leg_w // 2, leg_top + 2, back_x + leg_w // 2, leg_top + leg_h], JEANS_DARK, radius=4)
        # Paws.
        paw_y = leg_top + leg_h
        draw_ellipse(draw, [front_x - 8, paw_y - 2, front_x + 8, paw_y + 8], Paws)
    else:
        # Front/back pairs.
        spread = 8 + abs(stride) * 4
        for sx in (-spread, spread):
            x = cx + sx
            draw_round_rect(draw, [x - leg_w // 2, leg_top, x + leg_w // 2, leg_top + leg_h], JEANS, radius=4)
            # Paws.
            paw_y = leg_top + leg_h
            draw_ellipse(draw, [x - 8, paw_y - 2, x + 8, paw_y + 8], Paws)


def draw_arms(draw, cx, cy, direction, swing=0, pose="walk"):
    """Arms in hoodie sleeves."""
    is_side = direction in ("right", "left")
    is_back = direction == "up"
    body_top = cy - 4
    shoulder_y = body_top + 10
    arm_w = 11
    arm_h = 28

    if is_back:
        # Both arms at sides.
        for sx in (-16, 16):
            draw_round_rect(draw, [cx + sx - arm_w // 2, shoulder_y, cx + sx + arm_w // 2, shoulder_y + arm_h], HOODIE, radius=4)
            draw_ellipse(draw, [cx + sx - 6, shoulder_y + arm_h, cx + sx + 6, shoulder_y + arm_h + 8], Paws_SHADOW)
        return

    if is_side:
        side = 1 if direction == "right" else -1
        # Front arm swings with walk.
        front_x = cx + side * 22 - swing * 8
        front_y = shoulder_y + abs(swing) * 4
        draw_round_rect(draw, [front_x - arm_w // 2, front_y, front_x + arm_w // 2, front_y + arm_h], HOODIE, radius=4)
        draw_ellipse(draw, [front_x - 6, front_y + arm_h, front_x + 6, front_y + arm_h + 8], Paws)
        # Back arm.
        back_x = cx - side * 16 + swing * 6
        draw_round_rect(draw, [back_x - arm_w // 2, shoulder_y + 2, back_x + arm_w // 2, shoulder_y + arm_h], HOODIE_DARK, radius=4)
        draw_ellipse(draw, [back_x - 6, shoulder_y + arm_h, back_x + 6, shoulder_y + arm_h + 8], Paws_SHADOW)
    else:
        # Front view: arms swing opposite to legs.
        for i, sx in enumerate((-18, 18)):
            s = -swing if i == 0 else swing
            arm_x = cx + sx + s * 6
            arm_y = shoulder_y + abs(s) * 3
            draw_round_rect(draw, [arm_x - arm_w // 2, arm_y, arm_x + arm_w // 2, arm_y + arm_h], HOODIE, radius=4)
            draw_ellipse(draw, [arm_x - 6, arm_y + arm_h, arm_x + 6, arm_y + arm_h + 8], Paws)


def draw_full_bear(draw, col, row, frame_idx, direction, pose="walk"):
    cx, cy = cxcy(col, row)

    # Bobbing for walk.
    bob = 0
    stride = 0
    swing = 0
    if pose == "walk":
        bobs = [0, -3, 0, -3]
        strides = [0, 6, 0, -6]
        swings = [0, -8, 0, 8]
        bob = bobs[frame_idx]
        stride = strides[frame_idx]
        swing = swings[frame_idx]
    elif pose == "idle":
        # Gentle breathing / sway.
        bob = [0, -1, -2, -1][frame_idx]
    elif pose == "swim":
        bob = [0, -4, -2, -4][frame_idx]
        swing = [0, 10, 0, -10][frame_idx]
    elif pose == "attack":
        swing = [-12, -4, 16, 8][frame_idx]
        bob = [0, -2, -4, -2][frame_idx]
    elif pose == "push":
        bob = [0, -2, -4, -2][frame_idx]
        swing = [0, 6, 12, 6][frame_idx]

    cy += bob

    draw_jeans_legs(draw, cx, cy, direction, stride)
    draw_hoodie_body(draw, cx, cy, direction)
    draw_arms(draw, cx, cy, direction, swing, pose)
    draw_head(draw, cx, cy, direction, smile=True, eyes_open=True)


def draw_swim(draw, col, row, frame_idx):
    cx, cy = cxcy(col, row)
    bob = [0, -4, -2, -4][frame_idx]
    cy += bob

    # Submerged body.
    draw_round_rect(draw, [cx - 22, cy + 10, cx + 22, cy + 46], HOODIE, radius=8)
    # Head above water.
    draw_head(draw, cx, cy - 12, "down", smile=True, eyes_open=True)
    # Paddling arms.
    arm_y = cy + 18
    offset = [-18, -6, 6, 18][frame_idx]
    draw_ellipse(draw, [cx + offset - 8, arm_y, cx + offset + 8, arm_y + 12], Paws)


def draw_attack(draw, col, row, frame_idx):
    cx, cy = cxcy(col, row)
    draw_jeans_legs(draw, cx, cy, "down", 0)
    draw_hoodie_body(draw, cx, cy, "down")
    draw_arms(draw, cx, cy, "down", swing=[-12, -4, 16, 8][frame_idx], pose="attack")
    draw_head(draw, cx, cy, "down", smile=True, eyes_open=True)
    # Swipe arc.
    swipe_x = cx + [-34, -12, 36, 48][frame_idx]
    swipe_y = cy + [-24, -44, -34, 8][frame_idx]
    draw_ellipse(draw, [swipe_x - 10, swipe_y - 10, swipe_x + 10, swipe_y + 10], HOODIE_LIGHT)


def draw_push(draw, col, row, frame_idx):
    cx, cy = cxcy(col, row)
    lean = [0, 4, 8, 4][frame_idx]
    cx += lean
    draw_jeans_legs(draw, cx, cy, "down", 0)
    draw_hoodie_body(draw, cx, cy, "down")
    # Arms forward.
    arm_y = cy + 8
    reach = [0, 6, 12, 6][frame_idx]
    draw_round_rect(draw, [cx - 28 - reach, arm_y, cx - 6, arm_y + 10], HOODIE, radius=4)
    draw_round_rect(draw, [cx + 6, arm_y, cx + 28 + reach, arm_y + 10], HOODIE, radius=4)
    draw_head(draw, cx, cy, "down", smile=True, eyes_open=True)


def draw_idle_breathe(draw, col, row, frame_idx):
    cx, cy = cxcy(col, row)
    # Subtle scale/bob for breathing.
    bobs = [0, -1, -2, -1][frame_idx]
    scales = [1.0, 1.01, 1.02, 1.01][frame_idx]
    cy += bobs
    body_w = int(42 * scales)
    body_h = int(52 * scales)
    body_top = cy - 4
    draw_round_rect(draw, [cx - body_w // 2, body_top, cx + body_w // 2, body_top + body_h], HOODIE, radius=10)
    draw.line([(cx, body_top + 8), (cx, body_top + body_h - 8)], fill=HOODIE_DARK, width=2)
    draw_round_rect(draw, [cx - 12, body_top + 28, cx + 12, body_top + 42], HOODIE_DARK, radius=4)
    draw_ellipse(draw, [cx - 12, body_top + 4, cx + 12, body_top + 12], FUR)
    draw_jeans_legs(draw, cx, cy, "down", 0)
    draw_arms(draw, cx, cy, "down", 0, "idle")
    # Blink on frames 1 and 3.
    eyes_open = frame_idx not in (1, 3)
    draw_head(draw, cx, cy, "down", smile=True, eyes_open=eyes_open)


ROW_DRAWERS = [
    lambda d, c, r, f: draw_full_bear(d, c, r, f, "up", "walk"),
    lambda d, c, r, f: draw_full_bear(d, c, r, f, "right", "walk"),
    lambda d, c, r, f: draw_full_bear(d, c, r, f, "down", "walk"),
    lambda d, c, r, f: draw_full_bear(d, c, r, f, "left", "walk"),
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
