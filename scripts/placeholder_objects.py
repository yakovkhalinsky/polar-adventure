#!/usr/bin/env python3
"""Generate clean placeholder object and water tile textures."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "public/assets"
OUT.mkdir(parents=True, exist_ok=True)

TILE_W = 64
TILE_H = 32


def diamond_mask():
    """A 64x32 isometric diamond alpha mask."""
    mask = Image.new("L", (TILE_W, TILE_H), 0)
    draw = ImageDraw.Draw(mask)
    cx = TILE_W // 2
    cy = TILE_H // 2
    points = [(cx, 0), (TILE_W - 1, cy), (cx, TILE_H - 1), (0, cy)]
    draw.polygon(points, fill=255)
    return mask


def save_tile(name: str, base: Image.Image):
    out_path = OUT / f"tiles/{name}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tile = Image.new("RGBA", (TILE_W, TILE_H), (0, 0, 0, 0))
    tile.paste(base.resize((TILE_W, TILE_H), Image.Resampling.LANCZOS), (0, 0), diamond_mask())
    tile.save(out_path)
    print(f"saved {out_path}")


def make_water():
    base = Image.new("RGBA", (TILE_W, TILE_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)
    # Deep blue with lighter wave highlights.
    draw.polygon([(32, 0), (63, 16), (32, 31), (0, 16)], fill="#1a4d6e")
    draw.line([(12, 16), (28, 16)], fill="#2a6d9e", width=2)
    draw.line([(36, 20), (52, 20)], fill="#2a6d9e", width=2)
    save_tile("water", base)


def save_object(name: str, img: Image.Image):
    out_path = OUT / f"objects/{name}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f"saved {out_path}")


def make_rock():
    img = Image.new("RGBA", (48, 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Grey boulder.
    draw.ellipse([4, 12, 44, 38], fill="#6b7a85")
    draw.ellipse([8, 8, 38, 26], fill="#8a9aa5")
    draw.ellipse([18, 2, 32, 16], fill="#9aabbb")
    save_object("rock", img)


def make_iceberg():
    img = Image.new("RGBA", (56, 72), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Tall blue ice chunk.
    draw.polygon([(28, 0), (54, 60), (28, 70), (2, 60)], fill="#b8e3ff")
    draw.polygon([(28, 0), (54, 60), (38, 68)], fill="#7ec8f5")
    draw.polygon([(28, 0), (2, 60), (18, 68)], fill="#d8f2ff")
    save_object("iceberg", img)


def make_tree():
    img = Image.new("RGBA", (48, 72), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Trunk.
    draw.rectangle([20, 50, 28, 70], fill="#5c4033")
    # Snow-dusted pine layers.
    draw.polygon([(24, 4), (44, 30), (4, 30)], fill="#1f4d2b")
    draw.polygon([(24, 4), (44, 30), (34, 30)], fill="#0f3a1b")
    draw.polygon([(24, 20), (42, 46), (6, 46)], fill="#236133")
    draw.polygon([(24, 20), (42, 46), (34, 46)], fill="#164d24")
    # Snow caps.
    draw.polygon([(24, 4), (32, 16), (16, 16)], fill="#ffffff")
    draw.polygon([(24, 20), (34, 32), (14, 32)], fill="#ffffff")
    save_object("tree", img)


def make_snow_mound():
    img = Image.new("RGBA", (40, 24), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 6, 38, 22], fill="#e8f4ff")
    draw.ellipse([8, 0, 32, 14], fill="#ffffff")
    save_object("snow-mound", img)


def make_penguin():
    img = Image.new("RGBA", (48, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Body.
    draw.ellipse([8, 12, 40, 56], fill="#1a1a2e")
    # White belly.
    draw.ellipse([16, 18, 32, 48], fill="#ffffff")
    # Beak.
    draw.polygon([(20, 20), (28, 20), (24, 28)], fill="#f2a93b")
    # Eye.
    draw.ellipse([21, 14, 25, 18], fill="#ffffff")
    draw.ellipse([22, 15, 24, 17], fill="#000000")
    # Feet.
    draw.ellipse([12, 54, 24, 62], fill="#f2a93b")
    draw.ellipse([26, 54, 38, 62], fill="#f2a93b")
    # Flippers.
    draw.polygon([(4, 28), (10, 22), (10, 42)], fill="#1a1a2e")
    draw.polygon([(44, 28), (38, 22), (38, 42)], fill="#1a1a2e")
    save_object("penguin", img)


def make_fish():
    img = Image.new("RGBA", (36, 24), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 28, 20], fill="#b8e0ff")
    draw.polygon([(26, 12), (36, 4), (36, 20)], fill="#b8e0ff")
    draw.ellipse([14, 8, 18, 12], fill="#0b1d2e")
    save_object("fish", img)


def make_igloo():
    img = Image.new("RGBA", (64, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Dome.
    draw.arc([2, 12, 62, 48], 180, 0, fill="#e8f4ff", width=10)
    draw.ellipse([2, 12, 62, 46], fill="#d0e6f5")
    # Doorway.
    draw.arc([22, 26, 42, 48], 180, 0, fill="#0b1d2e", width=2)
    draw.rectangle([24, 36, 40, 48], fill="#1a3045")
    # Ice blocks lines.
    draw.line([(6, 30), (58, 30)], fill="#b8d4e8", width=1)
    draw.line([(10, 18), (54, 18)], fill="#b8d4e8", width=1)
    save_object("igloo", img)


def make_sign():
    img = Image.new("RGBA", (32, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Post.
    draw.rectangle([12, 24, 20, 48], fill="#5c4033")
    # Board.
    draw.rectangle([2, 4, 30, 28], fill="#7a5230")
    draw.rectangle([6, 8, 26, 24], fill="#603e24")
    # Snow cap.
    draw.polygon([(2, 4), (16, 0), (30, 4)], fill="#ffffff")
    save_object("sign", img)


def main():
    make_water()
    make_rock()
    make_iceberg()
    make_tree()
    make_snow_mound()
    make_penguin()
    make_fish()
    make_igloo()
    make_sign()


if __name__ == "__main__":
    main()
