import urllib.request
import json

url = "http://localhost:8000/api/auth/login"
data = json.dumps({"username": "boss", "password": "test123"}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req)
    print(f"Status: {resp.status}")
    body = resp.read().decode()
    parsed = json.loads(body)
    print(f"Token (first 50): {parsed.get('access_token', 'N/A')[:50]}...")
    
    # Test authenticated endpoint
    token = parsed.get("access_token")
    if token:
        req2 = urllib.request.Request("http://localhost:8000/api/agents/available", headers={"Authorization": f"Bearer {token}"})
        resp2 = urllib.request.urlopen(req2)
        print(f"\nAgents endpoint status: {resp2.status}")
        agents_body = resp2.read().decode()
        print(f"Response (first 200): {agents_body[:200]}")
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'read'):
        print(f"Response: {e.read().decode()}")
