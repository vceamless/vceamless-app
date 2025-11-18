import os
import json
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HTML_PATH = os.path.join(BASE_DIR, "data_staging", "raw_landing", "people_list_page.html")
OUT_PATH = os.path.join(BASE_DIR, "data_staging", "bronze", "people_list.json")

def main():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("ul#person-grid li.person-card")
    print(f"Found {len(cards)} person-card elements")

    data = []
    for li in cards:
        a = li.find("a")
        img = li.find("img")
        name_el = li.find("h4")
        role_el = li.find("p")

        href = a.get("href") if a else None
        slug = a.get("data-slug") if a else None
        classes = li.get("class", [])
        photo_url = img.get("src") if img else None
        photo_alt = img.get("alt") if img else None
        name = name_el.get_text(strip=True) if name_el else None
        role = role_el.get_text(strip=True) if role_el else None

        record = {
            "slug": slug,
            "name": name,
            "title": role,
            "detail_url": href,
            "photo_url": photo_url,
            "photo_alt": photo_alt,
            "card_tags": [c for c in classes if c != "person-card"],
            "raw_classes": classes,
        }
        data.append(record)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(data)} people to {OUT_PATH}")

    print("\nSample first 3 records:")
    for rec in data[:3]:
        print(json.dumps(rec, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
