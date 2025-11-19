import os
import json
import time
from pathlib import Path

import boto3
import requests

# --- Config ---

# Local bronze input
BASE_DIR = Path(__file__).resolve().parent.parent
BRONZE_COMPANIES_PATH = BASE_DIR / "data_staging" / "bronze" / "companies_list.json"

# Local raw landing output for detail pages
COMPANY_PAGES_DIR = BASE_DIR / "data_staging" / "raw_landing" / "company_pages"

# S3 config
BUCKET = os.getenv("RAW_BUCKET", "vceamless-raw-web-031561760771")
S3_BASE_PREFIX = "sf_ventures/raw_landing/company_pages"

# Control how many companies to fetch for testing, -1 for all
MAX_COMPANIES = -1

s3 = boto3.client("s3")

# --- Helpers ---

def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text

def save_local(slug: str, html: str) -> Path:
    COMPANY_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    path = COMPANY_PAGES_DIR / f"{slug}.html"
    path.write_text(html, encoding="utf-8")
    return path

def upload_s3(slug: str, html: str, ts: int):
    key = f"{S3_BASE_PREFIX}/{slug}_{ts}.html"
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=html.encode("utf-8"),
        ContentType="text/html",
    )
    return key

# --- Main ---

def main():
    if not BRONZE_COMPANIES_PATH.exists():
        raise FileNotFoundError(f"Missing bronze companies JSON at {BRONZE_COMPANIES_PATH}")

    with BRONZE_COMPANIES_PATH.open("r", encoding="utf-8") as f:
        companies = json.load(f)

    print(f"Loaded {len(companies)} companies from {BRONZE_COMPANIES_PATH}")

    to_process = companies
    if MAX_COMPANIES > 0:
        to_process = companies[:MAX_COMPANIES]

    print(f"Fetching detail pages for {len(to_process)} companies (MAX_COMPANIES={MAX_COMPANIES})")

    ts = int(time.time())
    count = 0

    for rec in to_process:
        slug = rec.get("slug")
        url = rec.get("detail_url")

        if not slug or not url:
            print(f"Skipping record with missing slug or detail_url: {rec}")
            continue

        # If local file already exists, skip to avoid re-hitting the site
        local_path = COMPANY_PAGES_DIR / f"{slug}.html"
        if local_path.exists():
            print(f"[SKIP] Local file already exists for slug={slug}: {local_path}")
            continue

        print(f"[FETCH] slug={slug} url={url}")
        html = fetch_html(url)

        saved_path = save_local(slug, html)
        s3_key = upload_s3(slug, html, ts)

        print(f"  -> saved local: {saved_path}")
        print(f"  -> uploaded s3://{BUCKET}/{s3_key}")

        count += 1

    print(f"\nDone. Processed {count} company detail pages.")

if __name__ == "__main__":
    main()
