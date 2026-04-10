#!/usr/bin/env python3
"""Investigate failed tests"""
import requests
import json

BASE = "http://localhost:8000"

print("=== TEST 3: Wrong password ===")
try:
    r = requests.post(f"{BASE}/api/auth/login", json={"username": "boss", "password": "wrongpassword"}, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:300]}")
except requests.exceptions.ConnectionError as e:
    print(f"ConnectionError: {e}")
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}")

print("\n=== TEST 13: PUT conversation ===")
# Login first
r = requests.post(f"{BASE}/api/auth/login", json={"username": "boss", "password": "test123"}, timeout=10)
token = r.json().get("access_token") or r.json().get("token")
headers = {"Authorization": f"Bearer {token}"}

# Create a conversation
r = requests.post(f"{BASE}/api/chat/conversations", headers=headers,
                  json={"agent_type": "core_management", "title": "QA Investigate"}, timeout=10)
print(f"Create: {r.status_code}")
cid = r.json().get("id") if r.status_code in (200, 201) else None

if cid:
    # Try PUT
    r = requests.put(f"{BASE}/api/chat/conversations/{cid}", headers=headers,
                     json={"title": "QA Updated"}, timeout=10)
    print(f"PUT status: {r.status_code} body: {r.text[:200]}")

    # Try PATCH
    r = requests.patch(f"{BASE}/api/chat/conversations/{cid}", headers=headers,
                       json={"title": "QA Updated"}, timeout=10)
    print(f"PATCH status: {r.status_code} body: {r.text[:200]}")

    # Cleanup
    requests.delete(f"{BASE}/api/chat/conversations/{cid}", headers=headers, timeout=5)

print("\n=== TEST 19: Pending approvals ===")
r = requests.get(f"{BASE}/api/approvals/pending", headers=headers, timeout=10)
print(f"GET /api/approvals/pending: {r.status_code} body: {r.text[:200]}")
# Try query parameter
r = requests.get(f"{BASE}/api/approvals?status=pending", headers=headers, timeout=10)
print(f"GET /api/approvals?status=pending: {r.status_code} body: {r.text[:200]}")

print("\n=== TEST 31: Root / endpoint ===")
r = requests.get(f"{BASE}/", timeout=10)
print(f"GET /: {r.status_code} body: {r.text[:200]}")
r = requests.get(f"{BASE}/api", timeout=10)
print(f"GET /api: {r.status_code} body: {r.text[:200]}")
r = requests.get(f"{BASE}/docs", timeout=10)
print(f"GET /docs: {r.status_code} body: {r.text[:200]}")

print("\n=== TEST 33: Op1 core_management ===")
r = requests.post(f"{BASE}/api/auth/login", json={"username": "op1", "password": "test123"}, timeout=10)
op1_token = r.json().get("access_token") or r.json().get("token")
op1_h = {"Authorization": f"Bearer {op1_token}"}

r = requests.post(f"{BASE}/api/agents/core_management/run", headers=op1_h, json={"params": {}}, timeout=15)
print(f"Op1 core_management/run: {r.status_code} body: {r.text[:300]}")

# Check if it's a concurrent run issue (409 = conflict)
r = requests.get(f"{BASE}/api/agents/runs?agent_type=core_management", headers=op1_h, timeout=10)
print(f"GET /api/agents/runs: {r.status_code} body: {r.text[:300]}")
