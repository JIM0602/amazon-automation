import requests
r = requests.post("http://localhost:8000/api/auth/login", json={"username": "boss", "password": "test123"}, timeout=10)
print(r.json().get("access_token") or r.json().get("token"))
