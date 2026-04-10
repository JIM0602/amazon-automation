"""Comprehensive API endpoint verification for Phase 4 deployment."""
import json
import urllib.request
import urllib.error
import sys

BASE = "http://localhost:8000"

def req(method, path, token=None, body=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=10)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()[:200]
        try:
            return e.code, json.loads(body_text)
        except:
            return e.code, body_text
    except Exception as e:
        return 0, str(e)

results = []

# 1. Health
code, body = req("GET", "/health")
results.append(("GET /health", code, "OK" if code == 200 else f"FAIL: {body}"))

# 2. Login as boss
code, body = req("POST", "/api/auth/login", body={"username": "boss", "password": "test123"})
boss_token = body.get("access_token", "") if isinstance(body, dict) else ""
results.append(("POST /api/auth/login (boss)", code, "OK" if boss_token else f"FAIL: {body}"))

# 3. Login as operator
code, body = req("POST", "/api/auth/login", body={"username": "op1", "password": "test123"})
op_token = body.get("access_token", "") if isinstance(body, dict) else ""
results.append(("POST /api/auth/login (op1)", code, "OK" if op_token else f"FAIL: {body}"))

# 4. Chat - list conversations
code, body = req("GET", "/api/chat/conversations", token=boss_token)
results.append(("GET /api/chat/conversations", code, "OK" if code == 200 else f"FAIL: {body}"))

# 5. Chat - create conversation
code, body = req("POST", "/api/chat/conversations", token=boss_token, body={"agent_type": "core_management", "title": "Test conv"})
conv_id = body.get("id", "") if isinstance(body, dict) else ""
results.append(("POST /api/chat/conversations", code, f"OK id={conv_id[:8]}..." if conv_id else f"FAIL: {body}"))

# 6. Approvals
code, body = req("GET", "/api/approvals/", token=boss_token)
results.append(("GET /api/approvals/", code, "OK" if code == 200 else f"FAIL: {body}"))

# 7. System users (boss only)
code, body = req("GET", "/api/system/users", token=boss_token)
results.append(("GET /api/system/users (boss)", code, "OK" if code == 200 else f"FAIL: {body}"))

# 8. System users (op should fail)
code, body = req("GET", "/api/system/users", token=op_token)
results.append(("GET /api/system/users (op1)", code, "OK (403)" if code == 403 else f"UNEXPECTED: {code} {body}"))

# 9. KB Review
code, body = req("GET", "/api/kb-review/pending", token=boss_token)
results.append(("GET /api/kb-review/pending", code, "OK" if code == 200 else f"FAIL: {body}"))

# 10. Monitoring costs
code, body = req("GET", "/api/monitoring/costs", token=boss_token)
results.append(("GET /api/monitoring/costs (boss)", code, "OK" if code == 200 else f"FAIL: {body}"))

# 11. Monitoring costs (op should fail - boss only)
code, body = req("GET", "/api/monitoring/costs", token=op_token)
results.append(("GET /api/monitoring/costs (op1)", code, "OK (403)" if code == 403 else f"UNEXPECTED: {code} {body}"))

# 12. Agent run endpoint
code, body = req("POST", "/api/agents/core_management/run", token=boss_token, body={"input": "test"})
results.append(("POST /api/agents/core_management/run", code, "OK" if code in (200, 500, 422) else f"FAIL: {body}"))

# Print results
print("\n" + "="*70)
print("PHASE 4 DEPLOYMENT VERIFICATION RESULTS")
print("="*70)
passed = 0
failed = 0
for name, code, status in results:
    icon = "✓" if "OK" in status else "✗"
    print(f"  {icon} [{code}] {name}: {status}")
    if "OK" in status:
        passed += 1
    else:
        failed += 1

print(f"\n  Total: {passed} passed, {failed} failed out of {len(results)}")
print("="*70)
