from pathlib import Path
import json

from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parents[2]

BRONZE_COMPANIES_LIST = BASE_DIR / "data_staging" / "bronze" / "companies_list.json"
COMPANY_PAGES_DIR = BASE_DIR / "data_staging" / "raw_landing" / "company_pages"

# Control how many companies to inspect
MAX_COMPANIES = 10


def summarize_company(slug: str, list_name: str):
    html_path = COMPANY_PAGES_DIR / f"{slug}.html"
    if not html_path.exists():
        print(f"\n[WARN] No detail HTML for slug={slug} at {html_path}")
        return

    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    profile = soup.select_one("div.profile") or soup
    info_section = profile.select_one("section.profile-info")
    image_section = profile.select_one("section.profile-image.profile-image--company")

    # detail_name from logo alt or title text
    detail_name = None
    if info_section:
        title_img = info_section.select_one("h1.profile-title img")
        if title_img and title_img.get("alt"):
            detail_name = title_img.get("alt").strip()
        else:
            title_el = info_section.select_one("h1.profile-title")
            if title_el:
                detail_name = title_el.get_text(" ", strip=True) or None

    # description snippet
    desc_snippet = None
    if info_section:
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in info_section.find_all("p", recursive=False)
        ]
        if paragraphs:
            joined = "\n\n".join(paragraphs)
            desc_snippet = joined[:240] + ("..." if len(joined) > 240 else "")

    # website
    website_url = None
    website_empty = False
    if info_section:
        website_a = info_section.select_one("a.profile__link")
        if website_a:
            href = website_a.get("href", "").strip()
            if href:
                website_url = href
            else:
                website_empty = True

    # social links presence
    socials = {"twitter": None, "linkedin": None, "other_count": 0}
    if info_section:
        links = info_section.select("div.social-list.profile-social-list a")
        other = 0
        for a in links:
            href = a.get("href") or ""
            classes = a.get("class", [])
            href_lower = href.lower()
            if "social-icon__twitter" in classes or "twitter.com" in href_lower or "x.com" in href_lower:
                socials["twitter"] = href
            elif "social-icon__linkedin" in classes or "linkedin.com" in href_lower:
                socials["linkedin"] = href
            else:
                if href:
                    other += 1
        socials["other_count"] = other

    # info blocks (Leadership, Status, Acquired By, etc.)
    info_blocks = []
    if image_section:
        info_container = image_section.select_one("div.profile-image__info")
        if info_container:
            for h3 in info_container.select("h3.profile-more-info-subtitle"):
                label = h3.get_text(strip=True)
                block = h3.find_next_sibling("div", class_="profile-more-info")
                text = None
                if block:
                    text = " ".join(block.stripped_strings).strip() or None
                info_blocks.append({"label": label, "text": text})

    # print summary
    print("\n==============================")
    print(f"Slug:             {slug}")
    print(f"List name:        {list_name!r}")
    print(f"Detail name:      {detail_name!r}")
    print(f"Name mismatch?:   {detail_name != list_name if detail_name and list_name else 'n/a'}")

    print(f"\nDescription present?: {'yes' if desc_snippet else 'no'}")
    if desc_snippet:
        print(f"Description (snippet): {desc_snippet}")

    print(f"\nWebsite URL:      {website_url!r}")
    print(f"Website empty?:   {website_empty}")

    print("\nSocial links:")
    print(f"  twitter:        {socials['twitter']!r}")
    print(f"  linkedin:       {socials['linkedin']!r}")
    print(f"  other_count:    {socials['other_count']}")

    print("\nInfo blocks (label -> text):")
    if not info_blocks:
        print("  (none)")
    else:
        for blk in info_blocks:
            print(f"  - {blk['label']}: {blk['text']!r}")


def main():
    if not BRONZE_COMPANIES_LIST.exists():
        raise FileNotFoundError(f"Missing bronze companies list at {BRONZE_COMPANIES_LIST}")

    with BRONZE_COMPANIES_LIST.open("r", encoding="utf-8") as f:
        companies = json.load(f)

    print(f"Loaded {len(companies)} companies from {BRONZE_COMPANIES_LIST}")

    # Just inspect the first MAX_COMPANIES for now
    for rec in companies[:MAX_COMPANIES]:
        slug = rec.get("slug")
        list_name = rec.get("name")
        if not slug:
            print(f"[WARN] Skipping record with no slug: {rec}")
            continue
        summarize_company(slug, list_name)


if __name__ == "__main__":
    main()
