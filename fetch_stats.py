import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

URL = "https://commons.wikimedia.org/wiki/Special:MediaStatistics"
HEADERS = {
    "User-Agent": "CommonsMediaDashboardBot/1.0 (https://github.com/gnoeee/Commons-statistics)"
}
OUT_PATH = os.path.join("data", "media_stats.json")

# Special:MediaStatistics renders one table per section; the section is
# encoded in the table class, e.g. "mw-mediastats-table-bitmap".
CATEGORY_LABELS = {
    "bitmap": "Bitmap images",
    "drawing": "Drawings (vector images)",
    "audio": "Audio",
    "video": "Videos",
    "multimedia": "Multimedia",
    "office": "Office",
    "text": "Text",
    "executable": "Executables",
    "archive": "Archives",
    "3d": "3D",
    "unknown": "Unknown",
}


def to_int(text):
    return int(text.replace(",", "")) if text else 0


def parse_percent(text):
    m = re.search(r"([\d.]+(?:e-?\d+)?)\s*%", text)
    return float(m.group(1)) if m else 0.0


def main():
    print("Fetching data from", URL)
    response = requests.get(URL, headers=HEADERS, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    entries = []
    for table in soup.select("table.mw-mediastats-table"):
        category = next(
            (c.replace("mw-mediastats-table-", "") for c in table.get("class", [])
             if c.startswith("mw-mediastats-table-")),
            "unknown",
        )
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            if len(cells) < 4:
                continue  # header row
            mime, exts, files_text, size_text = cells[:4]

            files_m = re.match(r"^\s*([\d,]+)", files_text)
            size_m = re.search(r"([\d,]+)\s*bytes", size_text)
            # Size cell looks like "116,730,460 bytes (111.32 MB; 0.00000999%)"
            size_pct_m = re.search(r";\s*([\d.]+(?:e-?\d+)?)\s*%", size_text)

            entries.append({
                "mime": mime,
                "ext": exts,
                "category": category,
                "category_label": CATEGORY_LABELS.get(category, category.title()),
                "files": to_int(files_m.group(1)) if files_m else 0,
                "percent": parse_percent(files_text),
                "size_bytes": to_int(size_m.group(1)) if size_m else 0,
                "size_percent": float(size_pct_m.group(1)) if size_pct_m else 0.0,
            })

    totals = {}
    total_m = re.search(
        r"Total file size for all ([\d,]+) files:\s*([\d,]+)\s*bytes", soup.get_text(" ")
    )
    if total_m:
        totals = {"files": to_int(total_m.group(1)), "size_bytes": to_int(total_m.group(2))}

    print(f"Extracted {len(entries)} entries")
    if not entries:
        # Don't overwrite good data with an empty file if the page layout changes.
        sys.exit("No entries parsed; page structure may have changed. Keeping existing data.")

    os.makedirs("data", exist_ok=True)
    out = {
        "source": URL,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totals": totals,
        "entries": entries,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print("Saved", OUT_PATH)


if __name__ == "__main__":
    main()
