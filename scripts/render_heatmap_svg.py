"""
render_heatmap_svg.py — render data/contributions.json as the classic
53-week x 7-day contribution grid, revealed with a diagonal slide-down
animation (plays once, then freezes — no infinite looping "glow").

Usage:
    python scripts/render_heatmap_svg.py
    python scripts/render_heatmap_svg.py -i data/contributions.json -o contrib-heatmap.svg
"""
import argparse
import calendar
import json
import os
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

# level 0 = none ... level 5 = a neon top end above GitHub's usual level 4,
# used here purely as a stylistic accent for the "best" days
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

CELL = 11
GAP = 3
LEFT_PAD = 30      # room for weekday labels
TOP_PAD = 34       # room for month labels
RIGHT_PAD = 16
BOTTOM_PAD = 40    # room for legend + stats line
BG_COLOR = "#0d1117"
TEXT_COLOR = "#8b949e"
FONT_FAMILY = "SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
CORNER_RADIUS = 10


def level_for_count(count: int, max_count: int) -> int:
    if count == 0:
        return 0
    if max_count <= 0:
        return 1
    ratio = count / max_count
    if ratio > 0.85:
        return 5
    if ratio > 0.6:
        return 4
    if ratio > 0.35:
        return 3
    if ratio > 0.1:
        return 2
    return 1


def build_weeks(days: list[dict]) -> list[list[dict | None]]:
    """Bucket days into GitHub-style weeks (columns), Sunday-start rows."""
    by_date = {datetime.strptime(d["date"], "%Y-%m-%d").date(): d for d in days}
    if not by_date:
        return []

    all_dates = sorted(by_date)
    start, end = all_dates[0], all_dates[-1]
    # roll start back to the preceding Sunday so week columns align
    start -= __import__("datetime").timedelta(days=(start.weekday() + 1) % 7)

    weeks: list[list[dict | None]] = []
    current = start
    week: list[dict | None] = []
    while current <= end:
        entry = by_date.get(current)
        week.append(entry)
        if len(week) == 7:
            weeks.append(week)
            week = []
        current += __import__("datetime").timedelta(days=1)
    if week:
        while len(week) < 7:
            week.append(None)
        weeks.append(week)
    return weeks


def month_label_positions(weeks: list[list[dict | None]]) -> list[tuple[int, str]]:
    labels = []
    last_month = None
    for col, week in enumerate(weeks):
        for cell in week:
            if cell is None:
                continue
            d = datetime.strptime(cell["date"], "%Y-%m-%d").date()
            if d.day <= 7 and d.month != last_month:
                labels.append((col, calendar.month_abbr[d.month]))
                last_month = d.month
            break
    return labels


def build_svg(data: dict, static: bool = False) -> str:
    days = data["days"]
    stats = data["stats"]
    max_count = max((d["count"] for d in days), default=0)
    weeks = build_weeks(days)
    n_weeks = len(weeks)

    width = LEFT_PAD + n_weeks * (CELL + GAP) + RIGHT_PAD
    height = TOP_PAD + 7 * (CELL + GAP) + BOTTOM_PAD

    style = f"""
    <style>
      .heatmap-bg {{ fill: {BG_COLOR}; }}
      .label {{ font-family: {FONT_FAMILY}; font-size: 11px; fill: {TEXT_COLOR}; }}
      .stats-line {{ font-family: {FONT_FAMILY}; font-size: 12px; fill: {TEXT_COLOR}; }}
      .cell {{
        opacity: 0;
        animation: reveal 0.35s ease-out forwards;
      }}
      @keyframes reveal {{
        from {{ opacity: 0; transform: translateY(-6px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
      }}
    </style>"""

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">',
    ]
    if not static:
        parts.append(style)
    parts.append(f'<rect class="heatmap-bg" x="0" y="0" width="{width}" height="{height}" rx="{CORNER_RADIUS}"/>')

    # month labels
    for col, label in month_label_positions(weeks):
        x = LEFT_PAD + col * (CELL + GAP)
        parts.append(f'<text x="{x}" y="{TOP_PAD - 10}" class="label">{label}</text>')

    # weekday labels (Mon/Wed/Fri, GitHub's convention)
    weekday_rows = {1: "Mon", 3: "Wed", 5: "Fri"}
    for row, label in weekday_rows.items():
        y = TOP_PAD + row * (CELL + GAP) + CELL - 1
        parts.append(f'<text x="0" y="{y}" class="label">{label}</text>')

    # cells, diagonal stagger: delay grows with (col + row)
    stagger_step = 0.012
    for col, week in enumerate(weeks):
        for row, cell in enumerate(week):
            x = LEFT_PAD + col * (CELL + GAP)
            y = TOP_PAD + row * (CELL + GAP)
            count = cell["count"] if cell else 0
            level = level_for_count(count, max_count)
            color = PALETTE[level]
            delay = (col + row) * stagger_step
            style_attr = "" if static else f' style="animation-delay:{delay:.3f}s"'
            class_attr = "" if static else ' class="cell"'
            title = f'{count} contributions on {cell["date"]}' if cell else ""
            parts.append(
                f'<rect{class_attr} x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="2" fill="{color}"{style_attr}>'
                + (f'<title>{title}</title>' if title else '') +
                '</rect>'
            )

    # legend: Less -> More
    legend_y = TOP_PAD + 7 * (CELL + GAP) + 22
    legend_x = LEFT_PAD
    parts.append(f'<text x="{legend_x}" y="{legend_y}" class="label">Less</text>')
    lx = legend_x + 34
    for lvl, color in enumerate(PALETTE):
        parts.append(f'<rect x="{lx}" y="{legend_y - 10}" width="{CELL}" height="{CELL}" rx="2" fill="{color}"/>')
        lx += CELL + GAP
    parts.append(f'<text x="{lx + 6}" y="{legend_y}" class="label">More</text>')

    # stats footer
    stats_y = legend_y + 20
    footer = (f'{stats["total_contributions"]:,} contributions in the last year · '
              f'current streak {stats["current_streak"]}d · longest streak {stats["longest_streak"]}d')
    parts.append(f'<text x="{LEFT_PAD}" y="{stats_y}" class="stats-line">{footer}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", default="data/contributions.json")
    ap.add_argument("-o", "--output", default="contrib-heatmap.svg")
    args = ap.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    static = os.environ.get("STATIC") == "1"
    svg = build_svg(data, static=static)

    Path(args.output).write_text(svg, encoding="utf-8")
    print(f"[render_heatmap_svg] wrote {args.output}")


if __name__ == "__main__":
    main()
