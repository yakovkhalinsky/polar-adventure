#!/usr/bin/env python3
"""
Post-process ComfyUI outputs into game-ready Phaser assets.
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets-src"
OUT = ROOT / "public/assets"

TILE_WIDTH = 64
TILE_HEIGHT = 32
SPRITE_SIZE = 64

DIRECTION_ORDER = ["north", "east", "south", "west"]
TILES = ["snow", "ice", "ice_cracks"]


def detect_background_color(img: Image.Image) -> tuple[int, int, int]:
    """Sample border points to estimate the solid generated background color."""
    width, height = img.size
    samples = []
    border = max(width, height) // 12
    points = [
        (border, border),
        (width - border - 1, border),
        (border, height - border - 1),
        (width - border - 1, height - border - 1),
        (width // 2, border),
        (width // 2, height - border - 1),
        (border, height // 2),
        (width - border - 1, height // 2),
    ]
    rgb = img.convert("RGB")
    for x, y in points:
        samples.append(rgb.getpixel((x, y)))

    samples.sort()
    return samples[len(samples) // 2]


def remove_background(img: Image.Image, tolerance: int = 55) -> Image.Image:
    """Remove the uniform generated background by color keying, producing a clean alpha channel."""
    img = img.convert("RGBA")
    bg = detect_background_color(img)

    pixels = list(img.getdata())
    new_pixels = []
    for r, g, b, a in pixels:
        if (
            abs(r - bg[0]) <= tolerance
            and abs(g - bg[1]) <= tolerance
            and abs(b - bg[2]) <= tolerance
        ):
            new_pixels.append((r, g, b, 0))
        else:
            new_pixels.append((r, g, b, 255))
    img.putdata(new_pixels)
    return img


def make_isometric_tile(img: Image.Image) -> Image.Image:
    """Crop a 64x32 diamond from the center of a square texture.

    The generated textures are 256x256 square images with the isometric tile
    centered. We take the flat top diamond of the tile, ignoring the 3D sides.
    """
    src_size = 256
    img = img.convert("RGBA").resize((src_size, src_size), Image.Resampling.LANCZOS)

    tile = Image.new("RGBA", (TILE_WIDTH, TILE_HEIGHT), (0, 0, 0, 0))
    cx = src_size / 2
    cy = src_size / 2
    # The generated tile top face spans roughly from left edge to right edge.
    # Diamond half-width in source space ~ src_size/2, half-height ~ src_size/4.
    half_w = src_size / 2 - 1  # 127
    half_h = src_size / 4 - 1  # 63

    for y in range(TILE_HEIGHT):
        for x in range(TILE_WIDTH):
            # Normalize to [-1, 1] inside the target diamond.
            nx = (x / (TILE_WIDTH - 1)) * 2 - 1
            ny = (y / (TILE_HEIGHT - 1)) * 2 - 1
            if abs(nx) + abs(ny) <= 1.0:
                sx = int(cx + nx * half_w)
                sy = int(cy + ny * half_h)
                tile.putpixel((x, y), img.getpixel((sx, sy)))
    return tile


def make_isometric_tile_masked(img: Image.Image) -> Image.Image:
    """Create a tile by first removing the background, then applying a diamond mask."""
    img = remove_background(img, tolerance=55)
    img = img.resize((TILE_WIDTH * 4, TILE_HEIGHT * 4), Image.Resampling.LANCZOS)

    tile = Image.new("RGBA", (TILE_WIDTH, TILE_HEIGHT), (0, 0, 0, 0))
    cx = img.width // 2
    cy = img.height // 2
    half_w = img.width // 2 - 1
    half_h = img.height // 2 - 1

    for y in range(TILE_HEIGHT):
        for x in range(TILE_WIDTH):
            nx = (x / (TILE_WIDTH - 1)) * 2 - 1
            ny = (y / (TILE_HEIGHT - 1)) * 2 - 1
            if abs(nx) + abs(ny) <= 1.0:
                sx = int(cx + nx * half_w)
                sy = int(cy + ny * half_h)
                tile.putpixel((x, y), img.getpixel((sx, sy)))
    return tile


def build_polar_bear_spritesheet() -> Image.Image:
    """Assemble a 4x4 spritesheet: 4 directions x 4 duplicate walk frames."""
    frames = []
    for direction in DIRECTION_ORDER:
        path = SRC / f"polar_bear_{direction}_00001_.png"
        img = Image.open(path)
        img = remove_background(img, tolerance=60)
        # Scale to fit sprite cell while preserving aspect ratio.
        img.thumbnail((SPRITE_SIZE, SPRITE_SIZE), Image.Resampling.LANCZOS)
        # Center on a 64x64 transparent canvas.
        canvas = Image.new("RGBA", (SPRITE_SIZE, SPRITE_SIZE), (0, 0, 0, 0))
        cx = (SPRITE_SIZE - img.width) // 2
        cy = (SPRITE_SIZE - img.height) // 2
        canvas.paste(img, (cx, cy), img)
        # Duplicate 4 times for a simple walk cycle.
        for _ in range(4):
            frames.append(canvas.copy())

    sheet = Image.new("RGBA", (SPRITE_SIZE * 4, SPRITE_SIZE * 4), (0, 0, 0, 0))
    for row, direction in enumerate(DIRECTION_ORDER):
        for col in range(4):
            idx = row * 4 + col
            sheet.paste(frames[idx], (col * SPRITE_SIZE, row * SPRITE_SIZE))
    return sheet


def build_tiles() -> dict[str, Image.Image]:
    """Generate diamond isometric tiles from square textures."""
    tiles = {}
    for name in TILES:
        path = SRC / f"tile_{name}_00001_.png"
        img = Image.open(path)
        tile = make_isometric_tile_masked(img)
        tiles[name] = tile
    return tiles


def save_manifest():
    manifest = {
        "polar-bear": {
            "sheet": "characters/polar-bear.png",
            "frameWidth": SPRITE_SIZE,
            "frameHeight": SPRITE_SIZE,
            "directionRows": {
                "north": 0,
                "east": 1,
                "south": 2,
                "west": 3,
            },
        },
        "tiles": {
            "snow": "tiles/snow.png",
            "ice": "tiles/ice.png",
            "ice-cracks": "tiles/ice-cracks.png",
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))


def main():
    (OUT / "characters").mkdir(parents=True, exist_ok=True)
    (OUT / "tiles").mkdir(parents=True, exist_ok=True)

    print("building polar bear spritesheet...")
    sheet = build_polar_bear_spritesheet()
    sheet_path = OUT / "characters/polar-bear.png"
    sheet.save(sheet_path)
    print(f"saved {sheet_path} ({sheet.width}x{sheet.height})")

    print("building isometric tiles...")
    tiles = build_tiles()
    for name, tile in tiles.items():
        out_name = name.replace("_", "-")
        tile_path = OUT / f"tiles/{out_name}.png"
        tile.save(tile_path)
        print(f"saved {tile_path} ({tile.width}x{tile.height})")

    save_manifest()
    print("saved assets/manifest.json")


if __name__ == "__main__":
    main()
