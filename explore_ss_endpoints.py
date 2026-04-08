#!/usr/bin/env python3
"""Explore all Seller Sprite v1 endpoints to find accessible ones."""
import httpx
from src.config import Settings

s = Settings()
API_KEY = s.SELLER_SPRITE_API_KEY
headers = {"secret-key": API_KEY}

# Try many possible endpoints based on common API patterns
endpoints = [
    # Market research variants
    ("GET", "/v1/market/research", {"marketplace": "US", "keyword": "dog leash"}),
    ("POST", "/v1/market/research", None),  # with json body
    ("GET", "/v1/market/overview", {"marketplace": "US", "keyword": "dog leash"}),
    
    # Keyword variants
    ("GET", "/v1/keyword/research", {"marketplace": "US", "keyword": "dog leash"}),
    ("POST", "/v1/keyword/research", None),
    ("GET", "/v1/keyword/mining", {"marketplace": "US", "keyword": "dog leash"}),
    ("POST", "/v1/keyword/mining", None),
    ("GET", "/v1/keyword/search", {"marketplace": "US", "keyword": "dog leash"}),
    
    # Product variants
    ("GET", "/v1/product/research", {"marketplace": "US", "keyword": "dog leash"}),
    ("POST", "/v1/product/research", None),
    
    # Traffic / reverse
    ("GET", "/v1/traffic/keyword", {"marketplace": "US", "asin": "B07H256MBK"}),
    ("POST", "/v1/traffic/keyword", None),
    ("GET", "/v1/traffic/search", {"marketplace": "US", "asin": "B07H256MBK"}),
    
    # Sales variants
    ("GET", "/v1/sales/prediction/asin", {"marketplace": "US", "asin": "B07H256MBK"}),
    ("GET", "/v1/asin/research", {"marketplace": "US", "asin": "B07H256MBK"}),
    
    # Node/category
    ("GET", "/v1/product/node", {"marketplace": "US", "nodeIdPath": "2975263011"}),
    ("GET", "/v1/category", {"marketplace": "US"}),
    
    # v2 variants (in case v1 isn't right)
    ("POST", "/v2/product/research", None),
    ("POST", "/v2/keyword/mining", None),
    ("POST", "/v2/traffic/keyword", None),
    
    # OpenAPI / docs
    ("GET", "/swagger-ui.html", None),
    ("GET", "/api-docs", None),
    ("GET", "/openapi.json", None),
    ("GET", "/v1", None),
]

json_body_kw = {"keyword": "dog leash", "marketplace": "US"}
json_body_asin = {"asin": "B07H256MBK", "marketplace": "US"}

with httpx.Client(timeout=15.0, base_url="https://api.sellersprite.com") as client:
    for method, path, params in endpoints:
        try:
            json_body = None
            if method == "POST":
                json_body = json_body_asin if "asin" in path or "traffic" in path else json_body_kw
            
            resp = client.request(method, path, headers=headers, params=params, json=json_body)
            code = ""
            try:
                data = resp.json()
                code = data.get("code", "")
            except:
                pass
            
            # Highlight non-UNAUTHORIZED responses
            if code != "ERROR_UNAUTHORIZED" and "ERROR_URL_NOT_FOUND" not in str(code):
                print(f"✅ {method:4s} {path:40s} | HTTP {resp.status_code} | code={code} | {resp.text[:300]}")
            else:
                print(f"❌ {method:4s} {path:40s} | HTTP {resp.status_code} | code={code}")
        except Exception as e:
            print(f"⚠️ {method:4s} {path:40s} | Error: {str(e)[:100]}")
