"""
make_info_card.py — hand-author a neofetch-style SVG info panel that
fades/slides its lines in on a short stagger, next to the ASCII portrait.

Edit the CARD_DATA dict below with your own info, then run:
    python scripts/make_info_card.py

Set STATIC=1 to emit a frozen final frame (useful for local Quick Look
previews, which don't run CSS animation timers).
"""
import os
import xml.sax.saxutils as sax
from pathlib import Path

# ---- edit this section with your own info -------------------------------
CARD_DATA = {
    "title": "om@github",
    "rows": [
        ("Now", "B.Tech IT @ VNR VJIET (GPA 8.79)"),
        ("Prev", "Frontend Dev Intern @ Techlearn Solution"),
        ("Stack", "Python · JS · React · Node.js · MongoDB"),
        ("Highlights", "Agentic AI UPI resolver, RL trading agent"),
        ("Location", "Hyderabad, India"),
    ],
}
# ---------------------------------------------------------------------------

FONT_FAMILY = "SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
BG_COLOR = "#0d1117"
TITLE_COLOR = "#58a6ff"
KEY_COLOR = "#7ee787"
VALUE_COLOR = "#c9d1d9"
DIVIDER_COLOR = "#30363d"
CORNER_RADIUS = 10


def build_svg(data: dict, static: bool = False) -> str:
    pad = 22
    line_h = 30
    title_h = 40
    key_col_w = 110

    width = 490
    height = title_h + pad + len(data["rows"]) * line_h + pad

    style = f"""
    <style>
      .card-bg {{ fill: {BG_COLOR}; }}
      .title {{ font-family: {FONT_FAMILY}; font-size: 16px; font-weight: 700; fill: {TITLE_COLOR}; }}
      .divider {{ stroke: {DIVIDER_COLOR}; stroke-width: 1; }}
      .key {{ font-family: {FONT_FAMILY}; font-size: 13px; font-weight: 600; fill: {KEY_COLOR}; }}
      .value {{ font-family: {FONT_FAMILY}; font-size: 13px; fill: {VALUE_COLOR}; }}
      .fade-row {{
        opacity: 0;
        animation: fade-in 0.45s ease-out forwards;
      }}
      @keyframes fade-in {{
        from {{ opacity: 0; transform: translateX(-6px); }}
        to   {{ opacity: 1; transform: translateX(0); }}
      }}
    </style>"""

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">',
    ]
    if not static:
        parts.append(style)

    parts.append(f'<rect class="card-bg" x="0" y="0" width="{width}" height="{height}" rx="{CORNER_RADIUS}"/>')
    parts.append(f'<text x="{pad}" y="{title_h - 12}" class="title">{sax.escape(data["title"])}</text>')
    parts.append(f'<line x1="{pad}" y1="{title_h}" x2="{width - pad}" y2="{title_h}" class="divider"/>')

    for i, (key, value) in enumerate(data["rows"]):
        y = title_h + pad + i * line_h + 14
        delay = 0.15 + i * 0.09
        row_style = "" if static else f' style="animation-delay:{delay:.3f}s"'
        group_class = "fade-row" if not static else ""
        class_attr = f' class="{group_class}"' if group_class else ""
        parts.append(f'<g{class_attr}{row_style}>')
        parts.append(f'  <text x="{pad}" y="{y}" class="key">{sax.escape(key)}</text>')
        parts.append(f'  <text x="{pad + key_col_w}" y="{y}" class="value">{sax.escape(value)}</text>')
        parts.append('</g>')

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    static = os.environ.get("STATIC") == "1"
    svg = build_svg(CARD_DATA, static=static)
    out = Path("info-card.svg")
    out.write_text(svg, encoding="utf-8")
    print(f"[make_info_card] wrote {out}")


if __name__ == "__main__":
    main()
