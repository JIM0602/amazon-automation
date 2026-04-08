#!/usr/bin/env python3
"""Check the status of a specific Amazon Ads report and create a new test report."""
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
if not access_token:
    print(f"Token error: {token_data}")
    sys.exit(1)
print(f"Token obtained: {access_token[:20]}...")

headers = {
    "Amazon-Advertising-API-ClientId": s.AMAZON_ADS_CLIENT_ID,
    "Amazon-Advertising-API-Scope": s.AMAZON_ADS_PROFILE_ID,
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
}

# 2. Check old report status
print("\n=== Step 2: Check Old Report (6f405525-...) ===")
old_report_id = "6f405525-1467-4c89-a998-fada32d281a1"
resp = requests.get(
    f"https://advertising-api.amazon.com/reporting/reports/{old_report_id}",
    headers=headers,
)
print(f"Status code: {resp.status_code}")
print(f"Response: {resp.text[:2000]}")

# 3. Create a NEW simple test report
print("\n=== Step 3: Create New Test Report ===")
from datetime import datetime, timedelta, timezone
today = datetime.now(timezone.utc).date()
end_date = (today - timedelta(days=3)).isoformat()  # 3 days ago (safe for data availability)
start_date = (today - timedelta(days=10)).isoformat()  # 10 days ago

payload = {
    "name": f"test_report_{start_date}_{end_date}",
    "startDate": start_date,
    "endDate": end_date,
    "configuration": {
        "adProduct": "SPONSORED_PRODUCTS",
        "groupBy": ["campaign"],
        "columns": ["campaignId", "campaignName", "impressions", "clicks", "cost"],
        "reportTypeId": "spCampaigns",
        "timeUnit": "SUMMARY",
        "format": "GZIP_JSON",
    },
}

create_headers = {
    **headers,
    "Content-Type": "application/vnd.createasyncreportrequest.v3+json",
}

print(f"Payload: {json.dumps(payload, indent=2)}")
resp2 = requests.post(
    "https://advertising-api.amazon.com/reporting/reports",
    headers=create_headers,
    json=payload,
)
print(f"Create status code: {resp2.status_code}")
print(f"Create response: {resp2.text[:2000]}")

if resp2.status_code in (200, 202):
    new_report = resp2.json()
    new_report_id = new_report.get("reportId", "")
    print(f"\nNew report ID: {new_report_id}")
    
    # 4. Poll for status a few times
    if new_report_id:
        import time
        print("\n=== Step 4: Poll New Report Status (10 polls, 10s interval) ===")
        for i in range(10):
            time.sleep(10)
            check_resp = requests.get(
                f"https://advertising-api.amazon.com/reporting/reports/{new_report_id}",
                headers=headers,
            )
            check_data = check_resp.json() if check_resp.status_code == 200 else {}
            status = check_data.get("status", "UNKNOWN")
            print(f"Poll {i+1}/10: status={status} | full={json.dumps(check_data)[:500]}")
            if status in ("COMPLETED", "FAILED", "CANCELLED"):
                if status == "COMPLETED":
                    url = check_data.get("url", "")
                    print(f"\n=== REPORT COMPLETED! Download URL: {url[:200]} ===")
                break
else:
    print(f"Failed to create report!")
