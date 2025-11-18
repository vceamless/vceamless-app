import os
import json
import time

import boto3

BUCKET = os.getenv("RAW_BUCKET", "vceamless-raw-web-031561760771")

s3 = boto3.client("s3")

def main():
    timestamp = int(time.time())
    payload = {
        "source": "sf_ventures_demo",
        "timestamp": timestamp,
        "message": "hello from vceamless ingestion"
    }
    key = f"sf_ventures/raw/test_payload_{timestamp}.json"

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(payload, indent=2).encode("utf-8")
    )

    print(f"Wrote s3://{BUCKET}/{key}")

if __name__ == "__main__":
    main()
