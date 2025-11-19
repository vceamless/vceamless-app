from pathlib import Path
import os
import json
from typing import Dict, Any, List, Optional

import boto3
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).resolve().parents[2]

BRONZE_COMPANIES_LIST = BASE_DIR / "data_staging" / "bronze" / "companies_list.json"
COMPANY_PAGES_DIR = BASE_DIR / "data_staging" / "raw_landing" / "company_pages"
OUT_PATH = BASE_DIR / "data_staging" / "bronze" / "companies_enriched.json"

# S3 config for mirroring enriched bronze
BUCKET = os.getenv("RAW_BUCKET", "vceamless-raw-web-031561760771")
BRONZE_S3_KEY = "sf_ventures/bronze/companies_enriched.json"

s3 = boto3.client("s3")


def normalize_label(label: str) -> str:
    """
    Turn 'Status' -> 'status_detail', 'Acquired By' -> 'acquired_by', etc.
    We keep 'leadership' special-cased elsewhere.
    """
    label = (label or "").strip()
    key = label.lower().replace(" ", "_")
    if key == "status":
        return "status_detail"
    return key


def parse_leadership_block(block) -> List[Dict[str, Optional[str]]]:
    """
    Parse leadership lines like 'Jeff Shiner, CEO' into [{name, role}, ...].
    """
    leaders: List[Dict[str, Optional[str]]] = []
    if not block:
        return leaders

    for seg in block.stripped_strings:
        text = seg.strip()
        if not text:
            continue
        # Split on first comma only
        if "," in text:
            name, role = text.split(",", 1)
            leaders.append({"name": name.strip(), "role": role.strip()})
        else:
            leaders.append({"name": text, "role": None})
    return leaders


def parse_social_links(info_section) -> Dict[str, Any]:
    """
    Extract social links (twitter/x, linkedin, other) from the profile-info section.
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
        else:
            others.append(href)

    if others:
        socials["other"] = others

    return socials


def parse_company_detail_html(html: str) -> Dict[str, Any]:
    """
    Given the HTML for a single company page, extract detail-level fields.
    """
    soup = BeautifulSoup(html, "html.parser")

    profile = soup.select_one("div.profile") or soup
    info_section = profile.select_one("section.profile-info")
    image_section = profile.select_one("section.profile-image.profile-image--company")

    data: Dict[str, Any] = {}

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
    data["detail_name"] = detail_name

    # Description: concatenated top-level <p> in profile-info
    description = None
    if info_section:
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in info_section.find_all("p", recursive=False)
        ]
        if paragraphs:
            description = "\n\n".join(paragraphs)
    data["description"] = description

    # Website (treat empty href as None)
    website_url = None
    if info_section:
        website_a = info_section.select_one("a.profile__link")
        if website_a:
            href = (website_a.get("href") or "").strip()
            if href:
                website_url = href
    data["website_url"] = website_url

    # Social links
    data["social_links"] = parse_social_links(info_section)

    # Hero image URL
    hero_image_url = None
    if image_section:
        hero_img = image_section.find("img")
        if hero_img and hero_img.get("src"):
            hero_image_url = hero_img.get("src")
    data["hero_image_url"] = hero_image_url

    # Info blocks (Leadership, Status, Acquired By, Region, etc.)
    info_blocks: Dict[str, Any] = {}
    leadership: List[Dict[str, Optional[str]]] = []

    if image_section:
        info_container = image_section.select_one("div.profile-image__info")
        if info_container:
            for h3 in info_container.select("h3.profile-more-info-subtitle"):
                label = h3.get_text(strip=True)
                key = normalize_label(label)
                block = h3.find_next_sibling("div", class_="profile-more-info")

                if not block:
                    continue

                if label.lower().startswith("leadership"):
                    leadership = parse_leadership_block(block)
                else:
                    text = " ".join(block.stripped_strings).strip() or None
                    info_blocks[key] = text

    if leadership:
        data["leadership"] = leadership

    # Merge other info blocks (e.g., status_detail, acquired_by, region)
    data.update(info_blocks)

    return data


def main():
    if not BRONZE_COMPANIES_LIST.exists():
        raise FileNotFoundError(f"Missing bronze companies list at {BRONZE_COMPANIES_LIST}")

    with BRONZE_COMPANIES_LIST.open("r", encoding="utf-8") as f:
        companies = json.load(f)

    print(f"Loaded {len(companies)} companies from {BRONZE_COMPANIES_LIST}")

    enriched = []
    missing_html = 0

    for rec in companies:
        slug = rec.get("slug")
        if not slug:
            print(f"[WARN] Skipping record with no slug: {rec}")
            continue

        html_path = COMPANY_PAGES_DIR / f"{slug}.html"
        if not html_path.exists():
            print(f"[WARN] No detail HTML found for slug={slug} at {html_path}")
            # keep the base record so we don't drop it from the dataset
            enriched.append(rec)
            missing_html += 1
            continue

        html = html_path.read_text(encoding="utf-8")
        detail_data = parse_company_detail_html(html)

        # Merge base list-level record with detail-level fields
        merged = {**rec, **detail_data}
        enriched.append(merged)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(enriched, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote {len(enriched)} enriched companies to {OUT_PATH}")
    if missing_html:
        print(f"[INFO] {missing_html} companies had no detail HTML and were left un-enriched.")

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
