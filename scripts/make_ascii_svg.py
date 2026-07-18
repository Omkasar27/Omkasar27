"""
make_ascii_svg.py — convert a prepped grayscale photo into a monochrome
ASCII-art SVG that "types" itself in row by row when GitHub loads it.

Usage:
    python scripts/make_ascii_svg.py source-prepped.png
    python scripts/make_ascii_svg.py source-prepped.png -o avi-ascii.svg --cols 100

Design choices (see the blog post for why):
    - Monochrome fill only. Per-character color mapping reads as noisy
      static, not a portrait.
    - A leading space in the ramp maps bright/background pixels to
      nothing, so only the subject prints.
    - Each row wipes in left-to-right with a small "cursor" block riding
      the edge, staggered top to bottom. It plays once and freezes —
      no looping.
    - All animation lives in inline <style>/CSS inside the SVG itself,
      since GitHub renders this file as a separate image resource (via
      <img src>) rather than parsing it as part of the Markdown, so none
      of Markdown's inline-style/script stripping applies here.
"""
import argparse
import xml.sax.saxutils as sax
from pathlib import Path

from PIL import Image

# bright (sparse) -> dark (dense); leading space clears background to nothing
RAMP = " .`:-=+*cs#%@"

FONT_FAMILY = "SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
BG_COLOR = "#0d1117"       # GitHub dark-theme panel color, used for both themes
TEXT_COLOR = "#c9d1d9"
CURSOR_COLOR = "#58a6ff"
CORNER_RADIUS = 10


def image_to_grid(img: Image.Image, cols: int) -> list[str]:
    w, h = img.size
    # monospace chars are roughly 2x taller than wide, so sample fewer
    # rows than a naive aspect ratio would suggest to avoid vertical
    # stretching of the portrait
    rows = max(1, round(cols * (h / w) * 0.55))
    small = img.convert("L").resize((cols, rows), Image.Resampling.BOX)
    pixels = small.load()

    grid = []
    for y in range(rows):
        line = []
        for x in range(cols):
            brightness = pixels[x, y]              # 0 (black) - 255 (white)
            idx = round((1 - brightness / 255) * (len(RAMP) - 1))
            line.append(RAMP[idx])
        grid.append("".join(line))
    return grid


def build_svg(grid: list[str], font_size: int = 13, static: bool = False) -> str:
    cols = max(len(r) for r in grid)
    rows = len(grid)

    char_w = font_size * 0.6
    line_h = font_size * 1.15
    pad = 18

    canvas_w = round(cols * char_w + pad * 2)
    canvas_h = round(rows * line_h + pad * 2)

    row_duration = 0.5
    row_stagger = 0.045

    style = f"""
    <style>
      .ascii-bg {{ fill: {BG_COLOR}; }}
      text {{
        font-family: {FONT_FAMILY};
        font-size: {font_size}px;
        fill: {TEXT_COLOR};
        white-space: pre;
      }}
      .cursor {{ fill: {CURSOR_COLOR}; }}
      @keyframes wipe {{
        from {{ width: 0; }}
        to   {{ width: {canvas_w}px; }}
      }}
      @keyframes cursor-move {{
        0%   {{ transform: translateX(0); opacity: 1; }}
        92%  {{ opacity: 1; }}
        100% {{ transform: translateX({canvas_w}px); opacity: 0; }}
      }}
      .wipe-rect {{
        animation: wipe {row_duration}s linear forwards;
      }}
      .cursor-rect {{
        animation: cursor-move {row_duration}s linear forwards;
      }}
    </style>"""

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" '
        f'width="{canvas_w}" height="{canvas_h}">',
    ]
    if not static:
        parts.append(style)
    parts.append(f'<rect class="ascii-bg" x="0" y="0" width="{canvas_w}" height="{canvas_h}" rx="{CORNER_RADIUS}"/>')

    for i, line in enumerate(grid):
        row_y = pad + (i + 1) * line_h - line_h * 0.25
        clip_id = f"clip-row-{i}"
        delay = i * row_stagger
        escaped = sax.escape(line)

        clip_w = canvas_w if static else 0
        style_attr = "" if static else f' style="animation-delay:{delay:.3f}s"'

        parts.append(f'<clipPath id="{clip_id}">')
        parts.append(
            f'  <rect class="wipe-rect" x="0" y="{pad + i * line_h}" '
            f'width="{clip_w}" height="{line_h + 2}"{style_attr}/>'
        )
        parts.append('</clipPath>')

        parts.append(f'<g clip-path="url(#{clip_id})">')
        parts.append(f'  <text x="{pad}" y="{row_y:.1f}" xml:space="preserve">{escaped}</text>')
        parts.append('</g>')

        if not static:
            parts.append(
                f'<rect class="cursor-rect" x="{pad}" y="{pad + i * line_h}" '
                f'width="{char_w:.1f}" height="{line_h:.1f}" style="animation-delay:{delay:.3f}s"/>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="prepped grayscale image (from prep_photo.py)")
    ap.add_argument("-o", "--output", default="avi-ascii.svg")
    ap.add_argument("--cols", type=int, default=100, help="character columns (default 100)")
    ap.add_argument("--font-size", type=int, default=13)
    args = ap.parse_args()

    img = Image.open(args.source)
    grid = image_to_grid(img, args.cols)
    static = __import__("os").environ.get("STATIC") == "1"
    svg = build_svg(grid, font_size=args.font_size, static=static)

    Path(args.output).write_text(svg, encoding="utf-8")
    print(f"[make_ascii_svg] wrote {args.output} ({len(grid)} rows x {args.cols} cols)")


if __name__ == "__main__":
    main()
