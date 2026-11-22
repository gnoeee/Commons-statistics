"""Build data/history.json from the git history of data/media_stats.json.

Each daily commit of media_stats.json is one snapshot. The output keeps one
snapshot per day (the last one), in a compact column layout for the
history player page (history.html).

Needs the full git history: in CI use actions/checkout with fetch-depth: 0.
"""
import json
import os
import statistics
import subprocess
from datetime import datetime, timezone

DATA_FILE = "data/media_stats.json"
OUT_PATH = os.path.join("data", "history.json")


def git(*args):
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout


def infer_categories(entries):
    """Older snapshots have no 'category'. The page lists sections in a fixed
    order, so the first application/ogg is Audio and the second Videos, and the
    first image/vnd.djvu is Bitmap and the second Office. Rows with the same
    (mime, category) in one snapshot are summed."""
    seen = {}
    for e in entries:
        if e.get("category"):
            continue
        m = e["mime"]
        n = seen.get(m, 0)
        seen[m] = n + 1
        if m == "application/ogg":
            # A third row (Multimedia section) appeared in some 2026 snapshots.
            e["category"] = ["audio", "video", "multimedia"][min(n, 2)]
        elif m == "image/vnd.djvu":
            e["category"] = "bitmap" if n == 0 else "office"
        elif m == "image/svg+xml":
            e["category"] = "drawing"
        elif m.startswith("image/"):
            e["category"] = "bitmap"
        elif m.startswith("audio/"):
            e["category"] = "audio"
        elif m.startswith("video/"):
            e["category"] = "video"
        elif m == "application/pdf":
            e["category"] = "office"
        elif "sla" in m or "stl" in m:
            e["category"] = "3d"
        else:
            e["category"] = "unknown"
    return entries


def load_snapshots():
    snaps = []
    log = git("log", "--reverse", "--format=%H %cI", "--", DATA_FILE).split("\n")
    for line in filter(None, log):
        sha, when = line.split()
        try:
            data = json.loads(git("show", f"{sha}:{DATA_FILE}"))
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            continue
        snaps.append((when, data))

    # Include the working-tree file too, so a fresh, not yet committed fetch
    # is part of the history built in the same CI run.
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            current = json.load(f)
        when = current.get("updated") or datetime.now(timezone.utc).isoformat()
        if not snaps or snaps[-1][1] != current:
            snaps.append((when, current))
    return snaps


def main():
    snaps = load_snapshots()
    if not snaps:
        raise SystemExit("No history found for " + DATA_FILE)

    # Normalise and keep the last snapshot of each day.
    by_day = {}
    for when, data in snaps:
        entries = data.get("entries") or []
        if not entries:
            continue
        infer_categories(entries)
        day = when[:10]
        by_day[day] = entries

    # Drop snapshots from early scraper bugs (wildly wrong file totals).
    totals = {d: sum(e["files"] for e in ents) for d, ents in by_day.items()}
    med = statistics.median(totals.values())
    days = sorted(d for d in by_day if 0.5 * med <= totals[d] <= 2 * med)
    dropped = len(by_day) - len(days)

    # Stable series list: (mime, category) pairs in first-seen order.
    series, index = [], {}
    for d in days:
        for e in by_day[d]:
            key = (e["mime"], e["category"])
            if key not in index:
                index[key] = len(series)
                series.append({"mime": e["mime"], "ext": e.get("ext", ""), "category": e["category"]})

    frames = []
    for d in days:
        files = [None] * len(series)
        size = [None] * len(series)
        for e in by_day[d]:
            i = index[(e["mime"], e["category"])]
            files[i] = (files[i] or 0) + e["files"]
            size[i] = (size[i] or 0) + e["size_bytes"]
        frames.append({"date": d, "files": files, "size": size})

    out = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "series": series,
        "frames": frames,
    }
    os.makedirs("data", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), ensure_ascii=False)
    print(f"Saved {OUT_PATH}: {len(frames)} days, {len(series)} series, dropped {dropped} bad snapshots")


if __name__ == "__main__":
    main()
