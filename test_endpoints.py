import urllib.request
import json

url = "http://localhost:8000/api/auth/login"
data = json.dumps({"username": "boss", "password": "test123"}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
token = json.loads(resp.read().decode())["access_token"]
print(f"Login OK. Token: {token[:50]}...")

# Test various endpoints
endpoints = [
    ("GET", "/health"),
    ("GET", "/api/chat/conversations"),
    ("GET", "/api/approvals/"),
    ("GET", "/api/system/users"),
    ("GET", "/api/monitoring/costs/summary"),
]

for method, path in endpoints:
    try:
        req = urllib.request.Request(
            f"http://localhost:8000{path}",
            headers={"Authorization": f"Bearer {token}"},
            method=method,
        )
        resp = urllib.request.urlopen(req)
        body = resp.read().decode()[:100]
        print(f"  {method} {path} -> {resp.status}: {body}")
    except Exception as e:
        code = e.code if hasattr(e, 'code') else 'N/A'
        body = e.read().decode()[:100] if hasattr(e, 'read') else str(e)
        print(f"  {method} {path} -> {code}: {body}")
