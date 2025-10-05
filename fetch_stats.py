import requests, re, json
from bs4 import BeautifulSoup

URL = "https://commons.wikimedia.org/wiki/Special:MediaStatistics"
HEADERS = {"User-Agent": "CommonsMediaDashboardBot/1.0"}

print("Fetching data from", URL)
html = requests.get(URL, headers=HEADERS).text
soup = BeautifulSoup(html, "html.parser")

data = []
for row in soup.select("table tr"):
    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
    if len(cells) >= 3 and any(prefix in cells[0] for prefix in ["image/", "audio/", "video/", "application/"]):
        mime = cells[0]
        exts = cells[1] if len(cells) > 1 else ""
        try:
            files = int(re.sub(r"[^0-9]", "", cells[2]))
        except:
            files = 0
        size_bytes_match = re.search(r"([0-9,]+) bytes", " ".join(cells))
        size_bytes = int(size_bytes_match.group(1).replace(",", "")) if size_bytes_match else 0
        data.append({"mime": mime, "ext": exts, "files": files, "size_bytes": size_bytes})

print(f"Extracted {len(data)} entries")
out = {"source": URL, "entries": data}
with open("data/media_stats.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("Saved data/media_stats.json ✅")
