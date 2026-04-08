#!/usr/bin/env python3
"""Test Seller Sprite MCP protocol directly."""
import json
import httpx
from src.config import Settings

s = Settings()
API_KEY = s.SELLER_SPRITE_API_KEY
MCP_ENDPOINT = s.SELLER_SPRITE_MCP_ENDPOINT

print(f"MCP endpoint: {MCP_ENDPOINT}")
print(f"API key: {API_KEY[:10]}...")

# MCP protocol: POST to endpoint with JSON-RPC 2.0
# Step 1: List available tools
print("\n=== Step 1: MCP tools/list ===")
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}
headers = {
    "Content-Type": "application/json",
    "secret-key": API_KEY,
}

with httpx.Client(timeout=30.0) as client:
    try:
        resp = client.post(MCP_ENDPOINT, headers=headers, json=payload)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        if "result" in data and "tools" in data["result"]:
            tools = data["result"]["tools"]
            print(f"Tools found: {len(tools)}")
            for t in tools:
                print(f"  - {t.get('name', '?')}: {t.get('description', '')[:100]}")
        else:
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)[:2000]}")
    except Exception as e:
        print(f"Error: {e}")

    # Step 2: Try calling a tool if found
    print("\n=== Step 2: Call keyword research tool ===")
    payload2 = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "keyword_research",  # guessing the tool name
            "arguments": {
                "keyword": "dog leash",
                "marketplace": "US",
            }
        }
    }
    try:
        resp2 = client.post(MCP_ENDPOINT, headers=headers, json=payload2)
        print(f"Status: {resp2.status_code}")
        print(f"Response: {resp2.text[:3000]}")
    except Exception as e:
        print(f"Error: {e}")
