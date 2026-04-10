"""Test SSE streaming endpoint."""
import json
import urllib.request

BASE = "http://localhost:8000"

# Login
data = json.dumps({"username": "boss", "password": "test123"}).encode()
req = urllib.request.Request(f"{BASE}/api/auth/login", data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
token = json.loads(resp.read().decode())["access_token"]

# Create a conversation first
data = json.dumps({"agent_type": "core_management", "title": "SSE Test"}).encode()
req = urllib.request.Request(f"{BASE}/api/chat/conversations", data=data, 
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
resp = urllib.request.urlopen(req)
conv = json.loads(resp.read().decode())
conv_id = conv["id"]
print(f"Created conversation: {conv_id}")

# Test SSE endpoint
data = json.dumps({"message": "Hello, what can you do?", "conversation_id": conv_id}).encode()
req = urllib.request.Request(f"{BASE}/api/chat/core_management/stream", data=data,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, method="POST")
try:
    resp = urllib.request.urlopen(req, timeout=15)
    content_type = resp.headers.get("Content-Type", "")
    print(f"Content-Type: {content_type}")
    
    # Read first few lines
    lines_read = 0
    for raw_line in resp:
        line = raw_line.decode().strip()
        if line:
            print(f"SSE: {line[:150]}")
            lines_read += 1
            if lines_read >= 10:
                break
    
    print(f"\nTotal SSE lines read: {lines_read}")
    if "text/event-stream" in content_type:
        print("SSE STREAMING: VERIFIED ✓")
    else:
        print(f"SSE STREAMING: Content-Type mismatch ({content_type})")
except Exception as e:
    print(f"SSE Error: {type(e).__name__}: {e}")
    if hasattr(e, 'read'):
        print(f"Response body: {e.read().decode()[:500]}")
