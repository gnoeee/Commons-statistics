import requests, re, json
from bs4 import BeautifulSoup

URL = "https://commons.wikimedia.org/wiki/Special:MediaStatistics"
html = requests.get(URL, headers={"User-Agent":"CommonsMediaDashboardBot/1.0"}).text
soup = BeautifulSoup(html, "html.parser")

data = []
# look for table rows that contain MIME stats
for row in soup.select("table tr"):
    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td","th"])]
    if len(cells) >= 4 and "image/" in cells[0] or "audio/" in cells[0] or "video/" in cells[0] or "application/" in cells[0]:
        mime = cells[0]
        exts = cells[1] if len(cells) > 1 else ""
        # extract numbers robustly
        files = int(re.sub(r"[^0-9]", "", cells[2])) if len(cells) > 2 else 0
        size_bytes_match = re.search(r"([0-9,]+) bytes", " ".join(cells))
        size_bytes = int(size_bytes_match.group(1).replace(",", "")) if size_bytes_match else 0
        data.append({"mime": mime, "ext": exts, "files": files, "size_bytes": size_bytes})

out = {"source": URL, "entries": data}
with open("data/media_stats.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print(f"Saved {len(data)} rows.")
