import os, requests, re, json
from bs4 import BeautifulSoup

URL = "https://commons.wikimedia.org/wiki/Special:MediaStatistics"
HEADERS = {"User-Agent": "CommonsMediaDashboardBot/1.0"}

print("Fetching data from", URL)
response = requests.get(URL, headers=HEADERS)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

data = []

for row in soup.select("table tr"):
    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]

    # Process only MIME-related rows
    if len(cells) >= 3 and any(prefix in cells[0] for prefix in ["image/", "audio/", "video/", "application/"]):
        mime = cells[0]
        exts = cells[1] if len(cells) > 1 else ""
        files_text = cells[2]
        file_match = re.match(r"^\s*([\d,]+)", files_text)
        files = int(file_match.group(1).replace(",", "")) if file_match else 0
        percent_match = re.search(r"\(([\d.]+)%\)", files_text)
        percent = float(percent_match.group(1)) if percent_match else 0.0
        size_bytes_match = re.search(r"([0-9,]+)\s*bytes", " ".join(cells))
        size_bytes = int(size_bytes_match.group(1).replace(",", "")) if size_bytes_match else 0

        data.append({
            "mime": mime,
            "ext": exts,
            "files": files,
            "percent": percent,
            "size_bytes": size_bytes
        })

print(f"Extracted {len(data)} entries")

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

out = {"source": URL, "entries": data}

# Save JSON
with open("data/media_stats.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print("Saved data/media_stats.json")
