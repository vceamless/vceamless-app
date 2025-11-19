from pathlib import Path
import os
import json
from typing import Dict, Any, List, Optional

import boto3
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parents[2]

BRONZE_PEOPLE_LIST = BASE_DIR / "data_staging" / "bronze" / "people_list.json"
PERSON_PAGES_DIR = BASE_DIR / "data_staging" / "raw_landing" / "person_pages"
OUT_PATH = BASE_DIR / "data_staging" / "bronze" / "people_enriched.json"

# S3 config for mirroring enriched bronze
BUCKET = os.getenv("RAW_BUCKET", "vceamless-raw-web-031561760771")
BRONZE_S3_KEY = "sf_ventures/bronze/people_enriched.json"

s3 = boto3.client("s3")


def parse_social_links(info_section) -> Dict[str, Any]:
    """
    Extract social links (twitter/x, linkedin, email, other) from the profile-info section.
    """
    socials: Dict[str, Any] = {}
    if not info_section:
        return socials

    links = info_section.select("div.social-list.profile-social-list a")
    others: List[str] = []

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
            others.append(href)

    if others:
        socials["other"] = others

    return socials


def parse_portfolio_companies(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Parse the optional portfolio companies section under
    <section class="companies-grid-wrapper companies-grid-wrapper--one-row">.
    """
    results: List[Dict[str, Any]] = []

    portco_section = soup.select_one("section.companies-grid-wrapper")
    if not portco_section:
        return results

    cards = portco_section.select("ul#companies-grid li.company-logo")
    for li in cards:
        a = li.find("a", class_="companies")
        img = li.find("img")

        company_slug = a.get("data-slug") if a else None
        classes = li.get("class", [])
        logo_alt = img.get("alt") if img else None

        # Clean name from alt, stripping trailing " logo"
        company_name = None
        if logo_alt:
            if logo_alt.lower().endswith(" logo"):
                company_name = logo_alt[: -len(" logo")].strip()
            else:
                company_name = logo_alt.strip()

        tags = [c for c in classes if c != "company-logo"]

        results.append(
            {
                "slug": company_slug,
                "name": company_name,
                "tags": tags,
            }
        )

    return results


def parse_person_detail_html(html: str) -> Dict[str, Any]:
    """
    Given the HTML for a single person page, extract detail-level fields.
    """
    soup = BeautifulSoup(html, "html.parser")

    profile = soup.select_one("div.profile") or soup
    info_section = profile.select_one("section.profile-info")
    image_section = profile.select_one("section.profile-image")

    data: Dict[str, Any] = {}

    detail_name = None
    detail_title = None
    description = None
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
            description = "\n\n".join(paragraphs)

        # Location in <small>
        small_el = info_section.select_one("small")
        if small_el:
            location = small_el.get_text(" ", strip=True) or None

    data["detail_name"] = detail_name
    data["detail_title"] = detail_title
    data["bio"] = description
    data["location"] = location

    # Social links
    data["social_links"] = parse_social_links(info_section)

    # Headshot image url (optional; we already have photo_url from list)
    headshot_url = None
    if image_section:
        img = image_section.find("img")
        if img and img.get("src"):
            headshot_url = img.get("src")
    data["detail_photo_url"] = headshot_url

    # Portfolio companies (optional section)
    data["portfolio_companies"] = parse_portfolio_companies(soup)

    return data


def main():
    if not BRONZE_PEOPLE_LIST.exists():
        raise FileNotFoundError(f"Missing bronze people list at {BRONZE_PEOPLE_LIST}")

    with BRONZE_PEOPLE_LIST.open("r", encoding="utf-8") as f:
        people = json.load(f)

    print(f"Loaded {len(people)} people from {BRONZE_PEOPLE_LIST}")

    enriched: List[Dict[str, Any]] = []
    missing_html = 0

    for rec in people:
        slug = rec.get("slug")
        if not slug:
            print(f"[WARN] Skipping record with no slug: {rec}")
            continue

        html_path = PERSON_PAGES_DIR / f"{slug}.html"
        if not html_path.exists():
            print(f"[WARN] No detail HTML found for slug={slug} at {html_path}")
            # keep base record so we don't lose it from the dataset
            enriched.append(rec)
            missing_html += 1
            continue

        html = html_path.read_text(encoding="utf-8")
        detail_data = parse_person_detail_html(html)

        # Merge base list-level record with detail-level fields
        merged = {**rec, **detail_data}
        enriched.append(merged)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote {len(enriched)} enriched people to {OUT_PATH}")
    if missing_html:
        print(f"[INFO] {missing_html} people had no detail HTML and were left un-enriched.")

    # Optional: mirror to S3 bronze
    try:
        s3.put_object(
            Bucket=BUCKET,
            Key=BRONZE_S3_KEY,
            Body=json.dumps(enriched, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        print(f"Uploaded enriched JSON to s3://{BUCKET}/{BRONZE_S3_KEY}")
    except Exception as e:
        print(f"[WARN] Failed to upload enriched JSON to S3: {e}")

    # Print a small sample
    print("\nSample of first 2 enriched records:")
    for rec in enriched[:2]:
        print(json.dumps(rec, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
