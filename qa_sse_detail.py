import requests
BASE = "http://localhost:8000"

# Login as boss
r = requests.post(f"{BASE}/api/auth/login", json={"username": "boss", "password": "test123"}, timeout=10)
token = r.json().get("access_token") or r.json().get("token")
headers = {"Authorization": f"Bearer {token}"}

# Test brand_planning SSE - check if it streams at all (even error is a valid SSE response)
r = requests.post(f"{BASE}/api/chat/brand_planning/stream", headers=headers,
                  json={"message": "hello"}, timeout=15, stream=True)
ct = r.headers.get("content-type", "")
print(f"brand_planning SSE: status={r.status_code} content-type={ct}")
chunks = []
for i, chunk in enumerate(r.iter_content(chunk_size=512)):
    text = chunk.decode("utf-8", errors="replace")
    chunks.append(text)
    if i >= 5:
        break
r.close()
print(f"Chunks received: {len(chunks)}")
for i, c in enumerate(chunks):
    print(f"  chunk {i}: {c[:120]}")

# The error "cannot import 'override' from 'typing'" is a Python 3.11 vs 3.12 issue
# with anthropic/pydantic. The SSE endpoint works (returns event-stream), the underlying 
# agent has a dependency issue.
print(f"\nSSE endpoint functional: {r.status_code == 200 and 'text/event-stream' in ct}")
print("Note: brand_planning agent has runtime error (Python 3.11 typing.override missing)")
print("This is an environment/dependency issue, not an API endpoint issue")

# Additional: Test all available agent types for SSE
for agent in ["core_management", "selection", "competitor", "persona", "ad_monitor", "listing"]:
    try:
        r = requests.post(f"{BASE}/api/chat/{agent}/stream", headers=headers,
                          json={"message": "ping"}, timeout=10, stream=True)
        ct = r.headers.get("content-type", "")
        first_chunk = ""
        for chunk in r.iter_content(chunk_size=512):
            first_chunk = chunk.decode("utf-8", errors="replace")[:80]
            break
        r.close()
        print(f"  {agent}: {r.status_code} ct={ct[:30]} data={first_chunk[:60]}")
    except Exception as e:
        print(f"  {agent}: ERROR {e}")
