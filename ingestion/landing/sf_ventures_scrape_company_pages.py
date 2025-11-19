import os
import json
import time
from pathlib import Path

import boto3
import requests

# --- Config ---
BASE_DIR = Path(__file__).resolve().parents[2]

# Local bronze input
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
        # ------------------------------------------------------------------------------
        # NOTE ABOUT PRODUCTION INGESTION / RE-RUN CONTROL
        #
        # Currently, we skip scraping a company detail page if a *local* HTML file already
        # exists in `data_staging/raw_landing/company_pages/`. This is the correct behavior
        # for a local exploratory workflow, because:
        #
        #   - It avoids re-hitting the live website unnecessarily.
        #   - It keeps local iterations fast.
        #   - Local state is persistent across runs.
        #
        # HOWEVER, this logic is NOT sufficient for any production ingestion pipeline
        # (e.g., Airflow, ECS, Lambda, or containerized deployments), where:
        #
        #   - Local filesystem state is ephemeral or nonexistent.
        #   - Each task/container run should be idempotent.
        #   - Re-run behavior should be governed by *S3 state*, *metadata tables*, or
        #     *checkpoint markers*, not local files.
        #
        # In a real pipeline, this skip logic would be replaced with something like:
        #
        #   - Check whether `s3://<bucket>/sf_ventures/raw_landing/company_pages/<slug>_<ts>.html`
        #     already exists (HEAD request / list / or S3 Select).
        #
        #   - Or maintain a `scrape_log` table in DynamoDB, PostgreSQL, or Snowflake that
        #     records which slugs have been scraped, with timestamps.
        #
        #   - Or use a "run timestamp" pattern: always write new objects to
        #     `company_pages/<slug>_<ingest_run_ts>.html`, and point downstream logic to
        #     the latest run via metadata.
        #
        # This file keeps the local-skip logic intentionally simple for the demo phase.
        # DO NOT reuse this skip condition as-is in any orchestrated production environment.
        # ------------------------------------------------------------------------------

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
