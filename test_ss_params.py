#!/usr/bin/env python3
"""Try all parameter variants for Seller Sprite GET endpoints."""
import json
import httpx
from src.config import Settings

s = Settings()
API_KEY = s.SELLER_SPRITE_API_KEY
headers = {"secret-key": API_KEY}

# Possible parameter name variants for marketplace and keyword
test_cases = [
    # /v1/product/research - keyword search
    ("/v1/product/research", {
        "marketplace": "US",
        "keyword": "dog leash",
        "month": "2026-03",
    }),
    ("/v1/product/research", {
        "marketplace": "US", 
        "keywords": "dog leash",
    }),
    ("/v1/product/research", {
        "marketplace": "US",
        "q": "dog leash",
    }),
    ("/v1/product/research", {
        "marketplace": "US",
        "searchKeyword": "dog leash",
    }),
    # Try the market codes Amazon uses
    ("/v1/product/research", {
        "marketplace": "ATVPDKIKX0DER",
        "keyword": "dog leash",
    }),
    ("/v1/product/research", {
        "marketplace_id": "US",
        "keyword": "dog leash",
    }),
    ("/v1/product/research", {
        "country": "US",
        "keyword": "dog leash",
    }),
    # POST with JSON (try different content type)
    ("POST:/v1/product/research", {
        "marketplace": "US",
        "keyword": "dog leash",
        "month": "2026-03",
    }),
    # /v1/market/research
    ("/v1/market/research", {
        "marketplace": "US",
        "keyword": "dog leash",
        "month": "2026-03",
    }),
    ("/v1/market/research", {
        "marketplace": "US",
        "keyword": "dog leash",
        "yearMonth": "202603",
    }),
    ("/v1/market/research", {
        "marketplace": "US",
        "keyword": "dog leash",
    }),
    # /v1/traffic/keyword
    ("/v1/traffic/keyword", {
        "marketplace": "US",
        "asin": "B07H256MBK",
    }),
    ("/v1/traffic/keyword", {
        "marketplace": "US",
        "asin": "B07H256MBK",
        "month": "2026-03",
    }),
]

with httpx.Client(timeout=30.0, base_url="https://api.sellersprite.com") as client:
    for item in test_cases:
        if isinstance(item[0], str) and item[0].startswith("POST:"):
            path = item[0][5:]
            params = item[1]
            method = "POST"
            resp = client.post(path, headers=headers, json=params)
        else:
            path = item[0]
            params = item[1]
            method = "GET"
            resp = client.get(path, headers=headers, params=params)
        
        code = ""
        try:
            data = resp.json()
            code = data.get("code", "")
        except:
            pass
        
        emoji = "✅" if code == "OK" else "⚠️" if code not in ("ERROR_UNAUTHORIZED", "ERROR_URL_NOT_FOUND", "ERROR_SERVER_INTERNAL") else "❌"
        print(f"{emoji} {method:4s} {path:35s} params={params}")
        print(f"   → code={code} | {resp.text[:300]}")
        if code == "OK":
            print(f"\n🎉 SUCCESS! Full response:\n{resp.text[:5000]}")
