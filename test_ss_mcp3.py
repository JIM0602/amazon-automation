#!/usr/bin/env python3
"""Test Seller Sprite MCP Streamable HTTP protocol.

独立脚本 — 不依赖 src 模块，可直接在服务器上运行。
用法:
    python3 test_ss_mcp3.py

流程:
    1. initialize  → 获取 session
    2. tools/list  → 枚举可用工具
    3. tools/call  → 调用 asin_detail 工具做真实数据测试
"""

import json
import sys
import time

import httpx

# ---- 配置 ----
MCP_ENDPOINT = "https://mcp.sellersprite.com/mcp"
SECRET_KEY = "fb4d9975ef8f4c408715ac0de8e3f001"
TIMEOUT = 120.0  # seconds

session_id = None
request_counter = 0


def next_id():
    global request_counter
    request_counter += 1
    return request_counter


def send_jsonrpc(method, params, *, expect_response=True):
    """Send JSON-RPC 2.0 via Streamable HTTP, handle JSON and SSE responses."""
    global session_id
    rid = next_id() if expect_response else None

    payload = {"jsonrpc": "2.0", "method": method, "params": params}
    if rid is not None:
        payload["id"] = rid

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "secret-key": SECRET_KEY,
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    print(f"\n>>> {method} (id={rid})")

    with httpx.Client(timeout=TIMEOUT) as client:
        with client.stream("POST", MCP_ENDPOINT, headers=headers, json=payload) as response:
            # Capture session id
            sid = response.headers.get("mcp-session-id")
            if sid:
                session_id = sid
                print(f"    [session-id set: {sid[:30]}...]")

            ct = response.headers.get("content-type", "")
            status = response.status_code
            print(f"    status={status}  content-type={ct}")

            if not expect_response:
                response.read()
                print("    (notification — no response expected)")
                return None

            if "text/event-stream" in ct:
                # SSE mode
                print("    [SSE mode]")
                result = None
                event_count = 0
                for line in response.iter_lines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith(":"):
                        continue
                    if stripped.startswith("event:"):
                        event_count += 1
                        print(f"    SSE event #{event_count}: {stripped}")
                    if stripped.startswith("data:"):
                        data_str = stripped[5:].strip()
                        if not data_str:
                            continue
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            print(f"    SSE non-JSON data: {data_str[:200]}")
                            continue
                        if isinstance(data, dict) and data.get("id") == rid:
                            if "error" in data:
                                print(f"    ERROR: {json.dumps(data['error'], indent=2, ensure_ascii=False)}")
                                return data
                            result = data.get("result", {})
                            print(f"    Got result for id={rid}")
                            break
                if result is None:
                    print("    WARNING: No matching response in SSE stream")
                return result
            else:
                # JSON mode
                body = response.read()
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    print(f"    Invalid JSON: {body[:500]}")
                    return None
                if isinstance(data, dict) and "error" in data:
                    print(f"    ERROR: {json.dumps(data['error'], indent=2, ensure_ascii=False)}")
                    return data
                result = data.get("result", {}) if isinstance(data, dict) else data
                return result


def main():
    print("=" * 60)
    print("Seller Sprite MCP Streamable HTTP Test")
    print(f"Endpoint: {MCP_ENDPOINT}")
    print(f"Key: {SECRET_KEY[:10]}...{SECRET_KEY[-4:]}")
    print("=" * 60)

    # ---- Step 1: Initialize ----
    print("\n### Step 1: initialize")
    t0 = time.time()
    result = send_jsonrpc("initialize", {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"},
    })
    print(f"    Time: {time.time() - t0:.2f}s")
    if result:
        print(f"    Server info: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")
    else:
        print("    FAILED — no result from initialize")
        sys.exit(1)

    # ---- Step 1b: Send initialized notification ----
    print("\n### Step 1b: notifications/initialized")
    send_jsonrpc("notifications/initialized", {}, expect_response=False)

    # ---- Step 2: List tools ----
    print("\n### Step 2: tools/list")
    t0 = time.time()
    result = send_jsonrpc("tools/list", {})
    print(f"    Time: {time.time() - t0:.2f}s")
    if result and "tools" in result:
        tools = result["tools"]
        print(f"\n    Found {len(tools)} tools:")
        for t in tools:
            name = t.get("name", "?")
            desc = (t.get("description") or "")[:80]
            print(f"      - {name}: {desc}")
    else:
        print(f"    Result: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}")

    # ---- Step 3: Call a tool — asin_detail ----
    print("\n### Step 3: tools/call — asin_detail")
    t0 = time.time()
    result = send_jsonrpc("tools/call", {
        "name": "asin_detail",
        "arguments": {
            "marketplace": "US",
            "asin": "B08GHW4TBS",
        },
    })
    print(f"    Time: {time.time() - t0:.2f}s")
    if result:
        content = result.get("content", [])
        print(f"    Content items: {len(content)}")
        for i, item in enumerate(content):
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                # Try to parse as JSON for pretty print
                try:
                    parsed = json.loads(text)
                    # Show key fields
                    if isinstance(parsed, dict):
                        print(f"    Item {i} (JSON): keys={list(parsed.keys())[:10]}")
                        for k in ["asin", "title", "price", "rating", "bsrRank", "brand"]:
                            if k in parsed:
                                val = parsed[k]
                                if isinstance(val, str) and len(val) > 60:
                                    val = val[:60] + "..."
                                print(f"      {k}: {val}")
                except json.JSONDecodeError:
                    print(f"    Item {i} (text): {text[:200]}")
            else:
                print(f"    Item {i}: {json.dumps(item, ensure_ascii=False)[:200]}")
    else:
        print("    No result from tools/call")

    # ---- Step 4: Call keyword_miner ----
    print("\n### Step 4: tools/call — keyword_miner")
    t0 = time.time()
    result = send_jsonrpc("tools/call", {
        "name": "keyword_miner",
        "arguments": {
            "marketplace": "US",
            "keyword": "dog leash",
        },
    })
    print(f"    Time: {time.time() - t0:.2f}s")
    if result:
        content = result.get("content", [])
        print(f"    Content items: {len(content)}")
        for i, item in enumerate(content[:2]):  # Only show first 2
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        print(f"    Item {i} (JSON): keys={list(parsed.keys())[:10]}")
                    elif isinstance(parsed, list):
                        print(f"    Item {i} (JSON array): len={len(parsed)}")
                        if parsed:
                            print(f"      First item keys: {list(parsed[0].keys())[:10] if isinstance(parsed[0], dict) else '?'}")
                except json.JSONDecodeError:
                    print(f"    Item {i} (text): {text[:300]}")
    else:
        print("    No result from tools/call")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
