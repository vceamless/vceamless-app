from pathlib import Path
import json

from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parents[2]

BRONZE_PEOPLE_LIST = BASE_DIR / "data_staging" / "bronze" / "people_list.json"
PERSON_PAGES_DIR = BASE_DIR / "data_staging" / "raw_landing" / "person_pages"

# Control how many people to inspect
MAX_PEOPLE = 10


def summarize_person(slug: str, list_name: str, list_title: str):
    html_path = PERSON_PAGES_DIR / f"{slug}.html"
    if not html_path.exists():
        print(f"\n[WARN] No detail HTML for slug={slug} at {html_path}")
        return

    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # Core profile container + info section
    profile = soup.select_one("div.profile") or soup
    info_section = profile.select_one("section.profile-info")
    image_section = profile.select_one("section.profile-image")

    detail_name = None
    detail_title = None
    description_snippet = None
    location = None

    # Name & title
    if info_section:
        title_el = info_section.select_one("h1.profile-title")
        if title_el:
            detail_name = title_el.get_text(" ", strip=True) or None

        subtitle_el = info_section.select_one("h2.profile-subtitle")
        if subtitle_el:
            detail_title = subtitle_el.get_text(" ", strip=True) or None

        # Bio / description: direct <p> children
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in info_section.find_all("p", recursive=False)
        ]
        if paragraphs:
            joined = "\n\n".join(paragraphs)
            description_snippet = joined[:280] + ("..." if len(joined) > 280 else "")

        # Location in <small>
        small_el = info_section.select_one("small")
        if small_el:
            location = small_el.get_text(" ", strip=True) or None

    # Social links
    socials = {
        "twitter": None,
        "linkedin": None,
        "email": None,
        "other_count": 0,
    }
    if info_section:
        links = info_section.select("div.social-list.profile-social-list a")
        other = 0
        for a in links:
            href = (a.get("href") or "").strip()
            if not href:
                continue
            classes = a.get("class", [])
            href_lower = href.lower()

            if "social-icon__twitter" in classes or "twitter.com" in href_lower or "x.com" in href_lower:
                socials["twitter"] = href
            elif "social-icon__linkedin" in classes or "linkedin.com" in href_lower:
                socials["linkedin"] = href
            elif "social-icon__email" in classes or href_lower.startswith("mailto:"):
                socials["email"] = href
            else:
                other += 1

        socials["other_count"] = other

    # Portfolio companies section (optional)
    portco_section = soup.select_one("section.companies-grid-wrapper")
    has_portfolio = portco_section is not None
    portcos = []

    if portco_section:
        cards = portco_section.select("ul#companies-grid li.company-logo")
        for li in cards[:8]:  # just sample first 8 to keep output small
            a = li.find("a", class_="companies")
            img = li.find("img")

            company_slug = a.get("data-slug") if a else None
            classes = li.get("class", [])
            logo_alt = img.get("alt") if img else None

            # Clean name from alt where it ends with " logo"
            company_name = None
            if logo_alt:
                if logo_alt.lower().endswith(" logo"):
                    company_name = logo_alt[: -len(" logo")].strip()
                else:
                    company_name = logo_alt.strip()

            tags = [c for c in classes if c != "company-logo"]

            portcos.append(
                {
                    "slug": company_slug,
                    "name": company_name,
                    "tags": tags,
                }
            )

    # Print summary
    print("\n==============================")
    print(f"Slug:              {slug}")
    print(f"List name:         {list_name!r}")
    print(f"List title:        {list_title!r}")
    print(f"Detail name:       {detail_name!r}")
    print(f"Detail title:      {detail_title!r}")
    mismatch_name = detail_name != list_name if detail_name and list_name else "n/a"
    mismatch_title = detail_title != list_title if detail_title and list_title else "n/a"
    print(f"Name mismatch?:    {mismatch_name}")
    print(f"Title mismatch?:   {mismatch_title}")

    print(f"\nDescription present?: {'yes' if description_snippet else 'no'}")
    if description_snippet:
        print(f"Description (snippet): {description_snippet}")

    print(f"\nLocation:          {location!r}")

    print("\nSocial links:")
    print(f"  twitter:         {socials['twitter']!r}")
    print(f"  linkedin:        {socials['linkedin']!r}")
    print(f"  email:           {socials['email']!r}")
    print(f"  other_count:     {socials['other_count']}")

    print(f"\nPortfolio section present?: {'yes' if has_portfolio else 'no'}")
    if has_portfolio:
        print(f"  Number of portfolio cards (sampled): {len(portcos)}")
        if portcos:
            print("  Sample portfolio companies:")
            for pc in portcos[:5]:
                print(f"    - slug={pc['slug']!r}, name={pc['name']!r}, tags={pc['tags']}")


def main():
    if not BRONZE_PEOPLE_LIST.exists():
        raise FileNotFoundError(f"Missing bronze people list at {BRONZE_PEOPLE_LIST}")

    with BRONZE_PEOPLE_LIST.open("r", encoding="utf-8") as f:
        people = json.load(f)

    print(f"Loaded {len(people)} people from {BRONZE_PEOPLE_LIST}")

    for rec in people[:MAX_PEOPLE]:
        slug = rec.get("slug")
        list_name = rec.get("name")
        list_title = rec.get("title")
        if not slug:
            print(f"[WARN] Skipping record with no slug: {rec}")
            continue
        summarize_person(slug, list_name, list_title)


if __name__ == "__main__":
    main()
