#!/usr/bin/env python3
"""Quick MCP data inspection — show actual data from tool calls."""
import json
import httpx

EP = "https://mcp.sellersprite.com/mcp"
KEY = "fb4d9975ef8f4c408715ac0de8e3f001"
SID = None
CTR = 0

def call(method, params, expect=True):
    global SID, CTR
    CTR += 1
    rid = CTR if expect else None
    payload = {"jsonrpc": "2.0", "method": method, "params": params}
    if rid: payload["id"] = rid
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "secret-key": KEY}
    if SID: headers["Mcp-Session-Id"] = SID
    r = httpx.post(EP, headers=headers, json=payload, timeout=120.0)
    if r.headers.get("mcp-session-id"): SID = r.headers["mcp-session-id"]
    if not expect: return None
    data = r.json()
    return data.get("result", {})

# Init
call("initialize", {"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}})
call("notifications/initialized", {}, expect=False)

def call_tool(name, args):
    result = call("tools/call", {"name": name, "arguments": args})
    content = result.get("content", [])
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                return json.loads(item["text"])
            except: return item["text"]
    return result

# Test 1: asin_detail
print("=== asin_detail (B08GHW4TBS) ===")
d = call_tool("asin_detail", {"marketplace": "US", "asin": "B08GHW4TBS"})
if isinstance(d, dict) and "data" in d:
    info = d["data"]
    for k in ["asin","title","price","rating","ratings","bsrRank","brand","bsrLabel","monthlySales","category","nodeLabelPath"]:
        if k in info:
            v = info[k]
            if isinstance(v, str) and len(v) > 80: v = v[:80] + "..."
            print(f"  {k}: {v}")
else:
    print(f"  Raw: {json.dumps(d, ensure_ascii=False)[:500]}")

# Test 2: keyword_miner  
print("\n=== keyword_miner (dog leash) ===")
d = call_tool("keyword_miner", {"marketplace": "US", "keyword": "dog leash"})
if isinstance(d, dict) and "data" in d:
    data = d["data"]
    if isinstance(data, dict):
        items = data.get("items", data.get("list", []))
        print(f"  Total items: {len(items) if isinstance(items, list) else 'N/A'}")
        if isinstance(items, list) and items:
            for item in items[:3]:
                kw = item.get("keyword") or item.get("keywords") or "?"
                vol = item.get("searches") or item.get("searchVolume") or "?"
                print(f"    keyword={kw}  searches={vol}")
        else:
            print(f"  Data keys: {list(data.keys())[:15]}")
    elif isinstance(data, list):
        print(f"  Items: {len(data)}")
        if data:
            print(f"  First keys: {list(data[0].keys())[:10] if isinstance(data[0], dict) else '?'}")
else:
    print(f"  Raw: {json.dumps(d, ensure_ascii=False)[:500]}")

# Test 3: traffic_keyword (reverse lookup)
print("\n=== traffic_keyword (B08GHW4TBS) ===")
d = call_tool("traffic_keyword", {"marketplace": "US", "asin": "B08GHW4TBS"})
if isinstance(d, dict) and "data" in d:
    data = d["data"]
    if isinstance(data, dict):
        items = data.get("items", [])
        print(f"  Total: {data.get('total', '?')}")
        print(f"  Items returned: {len(items)}")
        if items:
            for item in items[:3]:
                kw = item.get("keyword", "?")
                vol = item.get("searches", "?")
                print(f"    keyword={kw}  searches={vol}")
else:
    print(f"  Raw: {json.dumps(d, ensure_ascii=False)[:500]}")

# Test 4: product_node (category)
print("\n=== product_node (pet supplies) ===")
d = call_tool("product_node", {"marketplace": "US", "keyword": "pet supplies"})
if isinstance(d, dict) and "data" in d:
    data = d["data"]
    if isinstance(data, list):
        print(f"  Categories found: {len(data)}")
        for cat in data[:3]:
            print(f"    {cat.get('nodeLabelPath', '?')}  products={cat.get('products', '?')}")
    elif isinstance(data, dict):
        print(f"  Data keys: {list(data.keys())[:10]}")
else:
    print(f"  Raw: {json.dumps(d, ensure_ascii=False)[:500]}")

print("\nDONE")
