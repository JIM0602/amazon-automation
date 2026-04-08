#!/usr/bin/env python3
"""Try different auth header formats for Seller Sprite API."""
import httpx
from src.config import Settings

s = Settings()
API_KEY = s.SELLER_SPRITE_API_KEY

# Try different authentication methods
auth_methods = [
    ("secret-key header", {"secret-key": API_KEY}),
    ("Authorization Bearer", {"Authorization": f"Bearer {API_KEY}"}),
    ("Authorization", {"Authorization": API_KEY}),
    ("X-API-Key header", {"X-API-Key": API_KEY}),
    ("api-key header", {"api-key": API_KEY}),
    ("apikey header", {"apikey": API_KEY}),
    ("token header", {"token": API_KEY}),
    ("secret_key header (underscore)", {"secret_key": API_KEY}),
    ("Secret-Key header (capital)", {"Secret-Key": API_KEY}),
]

url = "https://api.sellersprite.com/v1/product/research"
json_body = {"keyword": "dog leash", "marketplace": "US"}

with httpx.Client(timeout=30.0) as client:
    for desc, headers in auth_methods:
        try:
            resp = client.post(url, headers=headers, json=json_body)
            code = ""
            try:
                data = resp.json()
                code = data.get("code", "")
            except:
                pass
            status_emoji = "✅" if code not in ("ERROR_UNAUTHORIZED", "") else "❌"
            print(f"{status_emoji} {desc}: HTTP {resp.status_code} | code={code} | body={resp.text[:200]}")
        except Exception as e:
            print(f"❌ {desc}: Error: {e}")

# Also try with query parameter
print("\n--- Query parameter methods ---")
param_methods = [
    ("apiKey param", {"apiKey": API_KEY}),
    ("api_key param", {"api_key": API_KEY}),
    ("key param", {"key": API_KEY}),
    ("secret-key param", {"secret-key": API_KEY}),
    ("token param", {"token": API_KEY}),
]
for desc, extra_params in param_methods:
    try:
        params = {**extra_params, "keyword": "dog leash", "marketplace": "US"}
        resp = client.get(url, headers={}, params=params)
        code = ""
        try:
            data = resp.json()
            code = data.get("code", "")
        except:
            pass
        status_emoji = "✅" if code not in ("ERROR_UNAUTHORIZED", "") else "❌"
        print(f"{status_emoji} {desc}: HTTP {resp.status_code} | code={code} | body={resp.text[:200]}")
    except Exception as e:
        print(f"❌ {desc}: Error: {e}")
