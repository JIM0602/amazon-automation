#!/usr/bin/env python3
"""Test actual Seller Sprite API endpoints used in code."""
import json
import httpx
from src.config import Settings

s = Settings()
API_KEY = s.SELLER_SPRITE_API_KEY
headers = {"secret-key": API_KEY}

endpoints = [
    ("POST", "https://api.sellersprite.com/v1/product/research", None, {"keyword": "dog leash", "marketplace": "US"}),
    ("GET", "https://api.sellersprite.com/v1/sales/prediction/asin", {"asin": "B07H256MBK", "marketplace": "US"}, None),
    ("GET", "https://api.sellersprite.com/v1/product/node", {"marketplace": "US", "nodeIdPath": "2975263011"}, None),
    ("POST", "https://api.sellersprite.com/v1/traffic/keyword", None, {"asin": "B07H256MBK", "marketplace": "US"}),
]

with httpx.Client(timeout=30.0) as client:
    for method, url, params, json_body in endpoints:
        print(f"\n=== {method} {url} ===")
        try:
            resp = client.request(method, url, headers=headers, params=params, json=json_body)
            print(f"Status: {resp.status_code}")
            text = resp.text
            if len(text) > 1500:
                text = text[:1500] + "... (truncated)"
            print(f"Response: {text}")
        except Exception as e:
            print(f"Error: {e}")
