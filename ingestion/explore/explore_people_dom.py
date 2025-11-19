from bs4 import BeautifulSoup
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
HTML_PATH = os.path.join(BASE_DIR, "data_staging", "raw_landing", "people_list_page.html")

def main():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    # People live under <ul id="person-grid"> as <li class="person-card team">
    cards = soup.select("ul#person-grid li.person-card")
    print(f"Found {len(cards)} person-card elements")

    print("\n=== First 5 people ===")
    for i, li in enumerate(cards[:5]):
        a = li.find("a")
        img = li.find("img")
        name_el = li.find("h4")
        role_el = li.find("p")

        href = a.get("href") if a else None
        data_slug = a.get("data-slug") if a else None
        classes = li.get("class", [])
        img_alt = img.get("alt") if img else None
        name = name_el.get_text(strip=True) if name_el else None
        role = role_el.get_text(strip=True) if role_el else None

        print(f"\n--- Person #{i+1} ---")
        print(f"href:       {href}")
        print(f"data-slug:  {data_slug}")
        print(f"classes:    {classes}")
        print(f"img.alt:    {img_alt}")
        print(f"name:       {name}")
        print(f"role:       {role}")

if __name__ == "__main__":
    main()
