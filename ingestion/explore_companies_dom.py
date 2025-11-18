from bs4 import BeautifulSoup
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HTML_PATH = os.path.join(BASE_DIR, "data_staging", "raw_landing", "companies_list_page.html")

def main():
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    # Companies live under <ul id="companies-grid"> as <li class="company-logo ...">
    cards = soup.select("ul#companies-grid li.company-logo")
    print(f"Found {len(cards)} company-logo elements")

    print("\n=== First 5 companies ===")
    for i, li in enumerate(cards[:5]):
        a = li.find("a", class_="companies")
        img = li.find("img")

        href = a.get("href") if a else None
        data_slug = a.get("data-slug") if a else None
        data_which = a.get("data-which") if a else None
        classes = li.get("class", [])

        alt = img.get("alt") if img else None  # e.g. "1Password logo"

        print(f"\n--- Company #{i+1} ---")
        print(f"href:       {href}")
        print(f"data-slug:  {data_slug}")
        print(f"data-which: {data_which}")
        print(f"classes:    {classes}")
        print(f"img.alt:    {alt}")

if __name__ == "__main__":
    main()
