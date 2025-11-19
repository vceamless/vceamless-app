import os
import json
import time
from pathlib import Path

import boto3
import requests

# ------------------------------------------------------------------------------
# NOTE ABOUT PRODUCTION INGESTION / RE-RUN CONTROL
#
# Currently, we skip scraping a person detail page if a *local* HTML file already
# exists in `data_staging/raw_landing/person_pages/`. This is appropriate for a
# local exploratory workflow because it avoids re-hitting the live site and lets
# us iterate quickly with persistent local state.
#
# In a real production pipeline (Airflow, ECS, Lambda, etc.), local filesystem
# state is often ephemeral or nonexistent. In that case, re-run behavior should
# be controlled via:
#
#   - S3 state (checking for existing objects with a particular prefix), or
#   - A metadata table (e.g., DynamoDB/Postgres/Snowflake) recording which slugs
#     have been scraped and when, or
#   - A "run timestamp" pattern where each ingest run writes to a new prefix and
#     downstream consumers use the latest successful run.
#
# This script keeps the local-skip logic intentionally simple for demo purposes.
# Do not reuse this skip condition as-is for orchestrated production ingestion.
# ------------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

BRONZE_PEOPLE_PATH = BASE_DIR / "data_staging" / "bronze" / "people_list.json"
PERSON_PAGES_DIR = BASE_DIR / "data_staging" / "raw_landing" / "person_pages"

BUCKET = os.getenv("RAW_BUCKET", "vceamless-raw-web-031561760771")
S3_BASE_PREFIX = "sf_ventures/raw_landing/person_pages"

# Control how many people to fetch for testing, -1 for all
MAX_PEOPLE = -1

s3 = boto3.client("s3")


def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text


def save_local(slug: str, html: str) -> Path:
    PERSON_PAGES_DIR.mkdir(parents=True, exist_ok=True)
    path = PERSON_PAGES_DIR / f"{slug}.html"
    path.write_text(html, encoding="utf-8")
    return path


def upload_s3(slug: str, html: str, ts: int) -> str:
    key = f"{S3_BASE_PREFIX}/{slug}_{ts}.html"
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=html.encode("utf-8"),
        ContentType="text/html",
    )
    return key


def main():
    if not BRONZE_PEOPLE_PATH.exists():
        raise FileNotFoundError(f"Missing bronze people JSON at {BRONZE_PEOPLE_PATH}")

    with BRONZE_PEOPLE_PATH.open("r", encoding="utf-8") as f:
        people = json.load(f)

    print(f"Loaded {len(people)} people from {BRONZE_PEOPLE_PATH}")

    to_process = people
    if MAX_PEOPLE > 0:
        to_process = people[:MAX_PEOPLE]

    print(f"Fetching detail pages for {len(to_process)} people (MAX_PEOPLE={MAX_PEOPLE})")

    ts = int(time.time())
    count = 0

    for rec in to_process:
        slug = rec.get("slug")
        url = rec.get("detail_url")

        if not slug or not url:
            print(f"[SKIP] Missing slug or detail_url in record: {rec}")
            continue

        local_path = PERSON_PAGES_DIR / f"{slug}.html"
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

    print(f"\nDone. Processed {count} person detail pages.")


if __name__ == "__main__":
    main()
