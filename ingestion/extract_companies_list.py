import os
import json
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HTML_PATH = os.path.join(BASE_DIR, "data_staging", "raw_landing", "companies.html")
OUT_PATH = os.path.join(BASE_DIR, "data_staging", "bronze", "companies_list.json")

def classify_tags(classes):
    status = None
    fund_tags = []
    theme_tags = []

    for c in classes:
        if c in ("active", "exited"):
            status = c
        elif c.endswith("-fund"):
            fund_tags.append(c)
        elif c not in ("company-logo",):
            theme_tags.append(c)

    return status, fund_tags, theme_tags

def main():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("ul#companies-grid li.company-logo")
    print(f"Found {len(cards)} company-logo elements")

    data = []
    for li in cards:
        a = li.find("a", class_="companies")
        img = li.find("img")

        href = a.get("href") if a else None
        slug = a.get("data-slug") if a else None
        classes = li.get("class", [])

        logo_url = img.get("src") if img else None
        logo_alt = img.get("alt") if img else None

        name = None
        if logo_alt:
            name = logo_alt.replace(" logo", "").strip()

        status, fund_tags, theme_tags = classify_tags(classes)

        record = {
            "slug": slug,
            "name": name,
            "detail_url": href,
            "logo_url": logo_url,
            "logo_alt": logo_alt,
            "status": status,
            "fund_tags": fund_tags,
            "theme_tags": theme_tags,
            "raw_classes": classes,
        }
        data.append(record)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(data)} companies to {OUT_PATH}")

    print("\nSample first 3 records:")
    for rec in data[:3]:
        print(json.dumps(rec, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
