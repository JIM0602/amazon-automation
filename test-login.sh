#!/bin/bash
# Test login flow
echo "=== Test 1: Login ==="
RESPONSE=$(curl -s http://localhost/api/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"test123"}')
echo "Login response: $RESPONSE"

TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token','NO_TOKEN'))")
echo "Token: ${TOKEN:0:50}..."

echo ""
echo "=== Test 2: /api/auth/me with token ==="
ME_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost/api/auth/me)
echo "Me response: $ME_RESPONSE"

echo ""
echo "=== Test 3: /api/auth/me without token (should 401) ==="
NO_AUTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/auth/me)
echo "Status: $NO_AUTH"

echo ""
echo "=== Test 4: Frontend login page loads ==="
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/login)
echo "Login page status: $LOGIN_STATUS"

echo ""
echo "=== Test 5: Dashboard redirects without auth ==="
DASH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -L http://localhost/dashboard)
echo "Dashboard status: $DASH_STATUS"
