"""Test RBAC enforcement."""
import json
import urllib.request
import urllib.error

BASE = "http://localhost:8000"

def login(username):
    data = json.dumps({"username": username, "password": "test123"}).encode()
    req = urllib.request.Request(f"{BASE}/api/auth/login", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read().decode())["access_token"]

boss_token = login("boss")
op1_token = login("op1")

tests = [
    # (description, method, path, token, expected_code)
    ("Boss runs auditor", "POST", "/api/agents/auditor/run", boss_token, [200, 202]),
    ("Op1 runs auditor (should fail)", "POST", "/api/agents/auditor/run", op1_token, [403]),
    ("Boss SSE auditor", "POST", "/api/chat/auditor/stream", boss_token, [200]),
    ("Op1 SSE auditor (should fail)", "POST", "/api/chat/auditor/stream", op1_token, [403]),
    ("Boss views system users", "GET", "/api/system/users", boss_token, [200]),
    ("Op1 views system users (should fail)", "GET", "/api/system/users", op1_token, [403]),
    ("Boss views costs", "GET", "/api/monitoring/costs", boss_token, [200]),
    ("Op1 views costs (should fail)", "GET", "/api/monitoring/costs", op1_token, [403]),
    ("Op1 runs core_management (should work)", "POST", "/api/agents/core_management/run", op1_token, [200, 202]),
    ("Op1 lists conversations (should work)", "GET", "/api/chat/conversations", op1_token, [200]),
]

print("RBAC Verification Results:")
print("=" * 60)
for desc, method, path, token, expected in tests:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = json.dumps({"input": "test", "message": "test", "conversation_id": "00000000-0000-0000-0000-000000000000"}).encode() if method == "POST" else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        code = resp.status
        resp.read()  # consume
    except urllib.error.HTTPError as e:
        code = e.code
        e.read()  # consume
    except Exception as e:
        code = 0
    
    ok = code in expected
    icon = "✓" if ok else "✗"
    print(f"  {icon} [{code}] {desc} (expected {expected})")

print("=" * 60)
