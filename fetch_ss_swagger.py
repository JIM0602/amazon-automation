#!/usr/bin/env python3
"""Fetch Seller Sprite Swagger/OpenAPI docs and test GET endpoints."""
import json
import httpx
from src.config import Settings

s = Settings()
API_KEY = s.SELLER_SPRITE_API_KEY
headers = {"secret-key": API_KEY}

# 1. Try to get OpenAPI/Swagger spec
with httpx.Client(timeout=30.0, base_url="https://api.sellersprite.com") as client:
    # Common Springfox Swagger 2 endpoint
    for doc_path in ["/v2/api-docs", "/swagger-resources", "/v3/api-docs", "/v2/api-docs?group=default"]:
        try:
            resp = client.get(doc_path, headers=headers)
            if resp.status_code == 200 and len(resp.text) > 500:
                print(f"=== FOUND: {doc_path} (size={len(resp.text)}) ===")
                # Save to file for analysis
                with open(f"/tmp/ss_swagger.json", "w") as f:
                    f.write(resp.text)
                
                # Parse and show endpoints
                try:
                    spec = resp.json()
                    if "paths" in spec:
                        print(f"Paths found: {len(spec['paths'])}")
                        for path, methods in sorted(spec["paths"].items()):
                            for method, detail in methods.items():
                                if method.upper() in ("GET", "POST", "PUT", "DELETE"):
                                    params = detail.get("parameters", [])
                                    param_names = [p.get("name", "") for p in params if isinstance(p, dict)]
                                    summary = detail.get("summary", "")
                                    print(f"  {method.upper():6s} {path:50s} | {summary} | params={param_names}")
                    elif "apis" in spec:
                        # Swagger resources format
                        for api in spec["apis"]:
                            print(f"  API group: {api}")
                    else:
                        print(f"Keys: {list(spec.keys())[:20]}")
                        print(f"First 2000 chars: {resp.text[:2000]}")
                except Exception as e:
                    print(f"Parse error: {e}")
                    print(f"First 2000 chars: {resp.text[:2000]}")
                break
            else:
                print(f"  {doc_path}: HTTP {resp.status_code}, size={len(resp.text)}")
        except Exception as e:
            print(f"  {doc_path}: Error: {e}")

    # 2. Test GET /v1/product/research with proper params
    print("\n\n=== Test GET /v1/product/research ===")
    params = {
        "marketplace": "US",
        "keyword": "dog leash",
    }
    resp = client.get("/v1/product/research", headers=headers, params=params)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:2000]}")

    # 3. Test GET /v1/traffic/keyword with proper params
    print("\n=== Test GET /v1/traffic/keyword ===")
    params2 = {
        "marketplace": "US",
        "asin": "B07H256MBK",
    }
    resp2 = client.get("/v1/traffic/keyword", headers=headers, params=params2)
    print(f"Status: {resp2.status_code}")
    print(f"Response: {resp2.text[:2000]}")

    # 4. Test GET /v1/market/research with proper params
    print("\n=== Test GET /v1/market/research ===")
    params3 = {
        "marketplace": "US",
        "keyword": "dog leash",
    }
    resp3 = client.get("/v1/market/research", headers=headers, params=params3)
    print(f"Status: {resp3.status_code}")
    print(f"Response: {resp3.text[:2000]}")
