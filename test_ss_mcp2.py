#!/usr/bin/env python3
"""Test Seller Sprite MCP with different transport approaches."""
import json
import httpx
from src.config import Settings

s = Settings()
API_KEY = s.SELLER_SPRITE_API_KEY
MCP_ENDPOINT = s.SELLER_SPRITE_MCP_ENDPOINT

# MCP Streamable HTTP uses POST with specific Accept header
# Per the MCP spec, the client should send:
# Content-Type: application/json
# Accept: application/json, text/event-stream
# And may need to set up SSE

print(f"MCP endpoint: {MCP_ENDPOINT}")
print(f"API key: {API_KEY[:10]}...")

# Approach 1: Standard JSON-RPC with Accept header for SSE
headers_v1 = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "secret-key": API_KEY,
}

# Approach 2: Try with Authorization header
headers_v2 = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": f"Bearer {API_KEY}",
}

# Approach 3: MCP initialization - must call initialize first
initialize_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    }
}

tools_list_payload = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
}

with httpx.Client(timeout=30.0) as client:
    for name, headers in [("secret-key header", headers_v1), ("Bearer auth", headers_v2)]:
        print(f"\n=== Approach: {name} ===")
        
        # Step 1: Initialize
        print("  Initialize:")
        try:
            resp = client.post(MCP_ENDPOINT, headers=headers, json=initialize_payload)
            print(f"    Status: {resp.status_code}")
            print(f"    Headers: {dict(resp.headers)}")
            print(f"    Body: {resp.text[:1000]}")
        except Exception as e:
            print(f"    Error: {e}")

        # Step 2: List tools
        print("  Tools list:")
        try:
            resp2 = client.post(MCP_ENDPOINT, headers=headers, json=tools_list_payload)
            print(f"    Status: {resp2.status_code}")
            print(f"    Body: {resp2.text[:1000]}")
        except Exception as e:
            print(f"    Error: {e}")

    # Approach 3: Try GET request (some MCP servers use GET for SSE)
    print("\n=== Approach: GET with SSE ===")
    try:
        resp3 = client.get(MCP_ENDPOINT, headers={"secret-key": API_KEY, "Accept": "text/event-stream"})
        print(f"  Status: {resp3.status_code}")
        print(f"  Headers: {dict(resp3.headers)}")
        print(f"  Body: {resp3.text[:500]}")
    except Exception as e:
        print(f"  Error: {e}")

    # Approach 4: Try /sse or /message sub-paths
    print("\n=== Approach: /sse and /message sub-paths ===")
    for subpath in ["/sse", "/message", "/messages", ""]:
        url = MCP_ENDPOINT.rstrip("/") + subpath
        try:
            resp4 = client.get(url, headers={"secret-key": API_KEY, "Accept": "text/event-stream"})
            print(f"  GET {subpath or '/'}: Status {resp4.status_code}, size={len(resp4.text)}, content-type={resp4.headers.get('content-type', 'N/A')}")
            if resp4.status_code == 200 and len(resp4.text) > 0:
                print(f"    Body: {resp4.text[:300]}")
        except Exception as e:
            print(f"  GET {subpath or '/'}: Error: {e}")
