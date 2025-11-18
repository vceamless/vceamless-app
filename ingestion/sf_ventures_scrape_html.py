import os
import time
import boto3
import requests

BUCKET = os.getenv("RAW_BUCKET", "vceamless-raw-web-031561760771")
s3 = boto3.client("s3")

COMPANIES_URL = "https://salesforceventures.com/companies/"
PEOPLE_URL = "https://salesforceventures.com/people/"

def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text

def upload_raw_html(key: str, html: str):
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=html.encode("utf-8"),
        ContentType="text/html"
    )
    print(f"Uploaded: s3://{BUCKET}/{key}")

def main():
    ts = int(time.time())

    # Scrape companies page
    companies_html = fetch_html(COMPANIES_URL)
    companies_key = f"sf_ventures/raw/companies_{ts}.html"
    upload_raw_html(companies_key, companies_html)

    # Scrape people page
    people_html = fetch_html(PEOPLE_URL)
    people_key = f"sf_ventures/raw/people_{ts}.html"
    upload_raw_html(people_key, people_html)

if __name__ == "__main__":
    main()
