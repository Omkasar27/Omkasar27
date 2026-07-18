"""
fetch_contributions.py — pull a GitHub user's public contribution
calendar without any auth token, by scraping the same HTML fragment
GitHub's own profile page uses.

Usage:
    python scripts/fetch_contributions.py YOUR_USERNAME
    python scripts/fetch_contributions.py YOUR_USERNAME -o data/contributions.json

GitHub serves this at:
    https://github.com/users/<username>/contributions
It returns an HTML fragment (not full JSON) with one <td> per day,
carrying the date, contribution count, and a "level" class GitHub uses
for its own green shading. We parse that directly instead of the
GraphQL API, so no personal access token is required.
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

CONTRIB_URL = "https://github.com/users/{username}/contributions"
HEADERS = {"User-Agent": "Mozilla/5.0 (profile-readme-bot)"}


def fetch_html(username: str) -> str:
    resp = requests.get(CONTRIB_URL.format(username=username), headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    days = []

    # GitHub renders each day as a <td> with a data-date attribute and
    # either a data-level attribute or a "level" number inside its class,
    # depending on markup version. Handle both.
    cells = soup.select("td.ContributionCalendar-day, td[data-date]")
    for cell in cells:
        date = cell.get("data-date")
        if not date:
            continue
        level = cell.get("data-level")
        if level is None:
            # fall back to parsing from tooltip text "N contributions on ..."
            level = 0
        count = 0
        tooltip_id = cell.get("id")
        days.append({
            "date": date,
            "level": int(level) if level is not None else 0,
            "_tooltip_id": tooltip_id,
        })

    # contribution counts live in separate <tool-tip>/<span> elements
    # keyed by the day cell's id; merge them in
    tooltips = {t.get("for"): t.get_text(strip=True) for t in soup.select("tool-tip[for]")}
    for day in days:
        tip = tooltips.get(day.pop("_tooltip_id", None), "")
        digits = "".join(ch for ch in tip.split(" ")[0] if ch.isdigit())
        day["count"] = int(digits) if digits else 0

    days.sort(key=lambda d: d["date"])
    return days


def derive_stats(days: list[dict]) -> dict:
    total = sum(d["count"] for d in days)

    # current streak: walk backward from the most recent day
    current_streak = 0
    for d in reversed(days):
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    # longest streak anywhere in the window
    longest_streak = 0
    running = 0
    for d in days:
        if d["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    best_day = max(days, key=lambda d: d["count"], default=None)

    monthly = defaultdict(int)
    for d in days:
        month = d["date"][:7]  # YYYY-MM
        monthly[month] += d["count"]

    return {
        "total_contributions": total,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "monthly_totals": dict(sorted(monthly.items())),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("username")
    ap.add_argument("-o", "--output", default="data/contributions.json")
    args = ap.parse_args()

    try:
        html = fetch_html(args.username)
    except requests.RequestException as e:
        print(f"[fetch_contributions] request failed: {e}", file=sys.stderr)
        sys.exit(1)

    days = parse_days(html)
    if not days:
        print("[fetch_contributions] warning: parsed 0 days — GitHub may have "
              "changed its markup, check the CSS selectors in this script",
              file=sys.stderr)

    stats = derive_stats(days)
    out = {"username": args.username, "days": days, "stats": stats}

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"[fetch_contributions] wrote {out_path} ({len(days)} days, "
          f"{stats['total_contributions']} total contributions)")


if __name__ == "__main__":
    main()
