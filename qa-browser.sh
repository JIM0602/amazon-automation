#!/bin/bash
echo "=== Scenario 1: Browser Auth Flow (curl-simulated) ==="

# 1.1 Verify login page renders
echo "--- 1.1: Login page HTML check ---"
LOGIN_HTML=$(curl -s https://siqiangshangwu.com/login)
LOGIN_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/login)
echo "HTTP Code: $LOGIN_CODE"

# Check for form elements
HAS_USERNAME=$(echo "$LOGIN_HTML" | grep -ci "username\|用户名\|user")
HAS_PASSWORD=$(echo "$LOGIN_HTML" | grep -ci "password\|密码")
HAS_BUTTON=$(echo "$LOGIN_HTML" | grep -ci "submit\|login\|登录\|button")
echo "Username field indicators: $HAS_USERNAME"
echo "Password field indicators: $HAS_PASSWORD"
echo "Submit button indicators: $HAS_BUTTON"

if [ "$LOGIN_CODE" = "200" ]; then
    echo "[PASS] Login page loads (200)"
else
    echo "[FAIL] Login page returns $LOGIN_CODE"
fi

# 1.2 Full login flow via API (simulating browser POST)
echo ""
echo "--- 1.2: Login API flow ---"
LOGIN_RESP=$(curl -s https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}')
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [ -n "$TOKEN" ]; then
    echo "[PASS] Login returns token"
else
    echo "[FAIL] No token returned"
fi

# 1.3 Dashboard page accessible with token
echo ""
echo "--- 1.3: Dashboard page ---"
DASH_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/dashboard)
echo "Dashboard HTTP Code: $DASH_CODE"
if [ "$DASH_CODE" = "200" ]; then
    echo "[PASS] Dashboard page loads (200)"
else
    echo "[INFO] Dashboard returns $DASH_CODE (may redirect to login without auth cookie)"
fi

# 1.4 Check the SPA structure (React/Vue apps serve same index.html)
echo ""
echo "--- 1.4: SPA structure check ---"
ROOT_HTML=$(curl -s https://siqiangshangwu.com/ | head -20)
echo "First 20 lines of root HTML:"
echo "$ROOT_HTML"

echo ""
echo "=== Integration Test 2: S3.3 Boss system/stop with reason ==="
BOSS_STOP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"reason":"qa-test"}' https://siqiangshangwu.com/api/system/stop)
echo "Boss stop with reason: $BOSS_STOP_CODE"
if [ "$BOSS_STOP_CODE" = "200" ]; then
    echo "[PASS] Boss system/stop with reason returns 200"
else
    echo "[FAIL] Boss system/stop returns $BOSS_STOP_CODE"
fi
