"""Generate assets/icon.ico for the Photon application.

Produces a multi-resolution ICO file containing 16, 32, 48, 64, 128, and 256 px
frames.  Requires Pillow (``pip install Pillow``).

Run before building with PyInstaller:
    python scripts/generate_icon.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Design tokens (must stay in sync with photon/ui/theme.py visually)
# ---------------------------------------------------------------------------
BG_COLOR     = (13,  17,  23)    # Colors.BASE  #0d1117
HEX_COLOR    = (124, 58, 237)    # Colors.ACCENT_PRIMARY  #7c3aed
TEXT_COLOR   = (226, 232, 240)   # Colors.TEXT_PRIMARY  #e2e8f0

SIZES = [16, 32, 48, 64, 128, 256]


def _hex_points(cx: float, cy: float, r: float) -> list[tuple[float, float]]:
    """Return the six vertices of a flat-top hexagon centred at (cx, cy)."""
    return [
        (cx + r * math.cos(math.radians(60 * i + 30)),
         cy + r * math.sin(math.radians(60 * i + 30)))
        for i in range(6)
    ]


def render_frame(size: int) -> "Image.Image":
    """Render a single icon frame at *size* × *size* pixels."""
    from PIL import Image, ImageDraw, ImageFont

    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── Background circle (pill softens the boxy hex at small sizes) ──
    draw.ellipse([0, 0, size - 1, size - 1], fill=(*BG_COLOR, 255))

    # ── Hexagon outline ────────────────────────────────────────────────
    margin   = max(2, size * 0.10)
    r_outer  = (size / 2) - margin
    r_inner  = r_outer - max(1, size * 0.07)    # outline thickness
    cx, cy   = size / 2, size / 2

    outer_pts = _hex_points(cx, cy, r_outer)
    inner_pts = _hex_points(cx, cy, r_inner)

    # Draw filled hex then punch out the inner hex for an outline effect
    draw.polygon(outer_pts, fill=(*HEX_COLOR, 255))
    draw.polygon(inner_pts, fill=(*BG_COLOR, 255))

    # ── Letter "P" ────────────────────────────────────────────────────
    if size >= 32:
        font_size = max(8, int(size * 0.38))
        font = None
        # Try to load a system font; fall back to PIL default
        for candidate in [
            "arialbd.ttf",        # Windows Arial Bold
            "Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
            "/System/Library/Fonts/Helvetica.ttc",                   # macOS
        ]:
            try:
                font = ImageFont.truetype(candidate, font_size)
                break
            except (OSError, IOError):
                continue
        if font is None:
            try:
                font = ImageFont.load_default(size=font_size)
            except TypeError:
                font = ImageFont.load_default()

        # Centre the "P" glyph
        text = "P"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = cx - tw / 2 - bbox[0]
        ty = cy - th / 2 - bbox[1]
        draw.text((tx, ty), text, font=font, fill=(*TEXT_COLOR, 255))

    return img


def main() -> None:
    """Generate ``assets/icon.ico`` with all required sizes."""
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        print("ERROR: Pillow is required.  Run: pip install Pillow", file=sys.stderr)
        sys.exit(1)

    repo_root  = Path(__file__).resolve().parent.parent
    assets_dir = repo_root / "assets"
    assets_dir.mkdir(exist_ok=True)
    out_path   = assets_dir / "icon.ico"

    frames = [render_frame(s) for s in SIZES]

    # PIL saves multi-size ICO when passed a list of sizes
    frames[0].save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[1:],
    )
    print(f"Icon written to {out_path}  ({len(SIZES)} sizes: {SIZES})")


if __name__ == "__main__":
    main()
