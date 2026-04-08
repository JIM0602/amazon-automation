#!/usr/bin/env python3
"""Download the completed report and verify data."""
import gzip
import json
import sys
import requests

sys.path.insert(0, "/app")
from src.config import Settings

s = Settings()

# 1. Get fresh access token
print("=== Step 1: Get Access Token ===")
token_resp = requests.post("https://api.amazon.com/auth/o2/token", data={
    "grant_type": "refresh_token",
    "refresh_token": s.AMAZON_ADS_REFRESH_TOKEN,
    "client_id": s.AMAZON_ADS_CLIENT_ID,
    "client_secret": s.AMAZON_ADS_CLIENT_SECRET,
})
token_data = token_resp.json()
access_token = token_data.get("access_token", "")
print(f"Token status: {token_resp.status_code}")

headers = {
    "Amazon-Advertising-API-ClientId": s.AMAZON_ADS_CLIENT_ID,
    "Amazon-Advertising-API-Scope": s.AMAZON_ADS_PROFILE_ID,
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
}

# 2. Get the COMPLETED report URL
print("\n=== Step 2: Get Report URL ===")
old_report_id = "6f405525-1467-4c89-a998-fada32d281a1"
resp = requests.get(
    f"https://advertising-api.amazon.com/reporting/reports/{old_report_id}",
    headers=headers,
)
report_data = resp.json()
status = report_data.get("status")
url = report_data.get("url", "")
print(f"Status: {status}")
print(f"FileSize: {report_data.get('fileSize')}")
print(f"URL present: {bool(url)}")
print(f"URL (first 150 chars): {url[:150]}...")

# 3. Download and decompress the report
if url:
    print("\n=== Step 3: Download Report Data ===")
    dl_resp = requests.get(url)
    print(f"Download status: {dl_resp.status_code}")
    print(f"Content-Length: {len(dl_resp.content)}")
    
    # Try GZIP decompression
    try:
        decompressed = gzip.decompress(dl_resp.content).decode("utf-8")
        print(f"Decompressed size: {len(decompressed)}")
        data = json.loads(decompressed)
        print(f"Data type: {type(data)}")
        if isinstance(data, list):
            print(f"Number of records: {len(data)}")
            for i, record in enumerate(data[:5]):
                print(f"\n  Record {i+1}: {json.dumps(record, indent=2)}")
        elif isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
            # Check common wrapper keys
            for key in ("report", "data", "items"):
                if key in data:
                    items = data[key]
                    if isinstance(items, list):
                        print(f"  {key}: {len(items)} records")
                        for i, record in enumerate(items[:5]):
                            print(f"  Record {i+1}: {json.dumps(record, indent=2)}")
    except Exception as e:
        # Maybe it's not gzip
        print(f"GZIP failed: {e}, trying plain text...")
        text = dl_resp.content.decode("utf-8")
        print(f"Plain text (first 1000 chars): {text[:1000]}")

# 4. Also check the new report status
print("\n=== Step 4: Check New Report Status ===")
new_report_id = "11e635f0-35ca-475b-bab9-00b0b868f4c8"
resp2 = requests.get(
    f"https://advertising-api.amazon.com/reporting/reports/{new_report_id}",
    headers=headers,
)
new_data = resp2.json()
print(f"New report status: {new_data.get('status')}")
print(f"New report generatedAt: {new_data.get('generatedAt')}")
print(f"New report URL: {new_data.get('url', 'None')[:100] if new_data.get('url') else 'None'}")
