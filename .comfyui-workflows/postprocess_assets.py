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

# Color used as transparent background in ComfyUI workflow.
KEY_COLOR = (255, 0, 255)

DIRECTION_ORDER = ["north", "east", "south", "west"]
TILES = ["snow", "ice", "ice_cracks"]


def remove_background(img: Image.Image, tolerance: int = 45) -> Image.Image:
    """Remove the uniform background by sampling corners and color-keying."""
    img = img.convert("RGBA")
    width, height = img.size

    # Estimate background color from the four corners (offset a few pixels in).
    corners = [
        img.getpixel((5, 5)),
        img.getpixel((width - 6, 5)),
        img.getpixel((5, height - 6)),
        img.getpixel((width - 6, height - 6)),
    ]
    bg_r = sum(c[0] for c in corners) // 4
    bg_g = sum(c[1] for c in corners) // 4
    bg_b = sum(c[2] for c in corners) // 4

    pixels = list(img.getdata())
    new_pixels = []
    for r, g, b, a in pixels:
        if (
            abs(r - bg_r) <= tolerance
            and abs(g - bg_g) <= tolerance
            and abs(b - bg_b) <= tolerance
        ):
            new_pixels.append((r, g, b, 0))
        else:
            new_pixels.append((r, g, b, 255))
    img.putdata(new_pixels)
    return img


def make_isometric_tile(img: Image.Image, name: str) -> Image.Image:
    """Crop a 64x32 diamond from the center of a square texture."""
    size = max(TILE_WIDTH, TILE_HEIGHT * 2)
    img = img.convert("RGBA")
    # Resize source to a square that covers the diamond footprint.
    src = img.resize((size, size), Image.Resampling.LANCZOS)

    tile = Image.new("RGBA", (TILE_WIDTH, TILE_HEIGHT), (0, 0, 0, 0))
    # Diamond mask: pixels inside the isometric diamond are opaque.
    for y in range(TILE_HEIGHT):
        for x in range(TILE_WIDTH):
            # Normalized coordinates: center is (0,0), x in [-1,1], y in [-1,1]
            nx = (x / (TILE_WIDTH - 1)) * 2 - 1
            ny = (y / (TILE_HEIGHT - 1)) * 2 - 1
            if abs(nx) + abs(ny) <= 1.0:
                # Map diamond point back to source square coordinates.
                sx = int(((nx + 1) / 2) * (size - 1))
                sy = int(((ny + 1) / 2) * (size - 1))
                tile.putpixel((x, y), src.getpixel((sx, sy)))
    return tile


def build_polar_bear_spritesheet() -> Image.Image:
    """Assemble a 4x4 spritesheet: 4 directions x 4 duplicate walk frames."""
    frames = []
    for direction in DIRECTION_ORDER:
        path = SRC / f"polar_bear_{direction}_00001_.png"
        img = Image.open(path)
        img = remove_background(img)
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
        img = remove_background(img)
        tile = make_isometric_tile(img, name)
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
