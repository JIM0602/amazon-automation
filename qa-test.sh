#!/bin/bash
echo "========================================="
echo "PUDIWIND QA Test Suite - Phase 3a"
echo "========================================="
echo ""

PASS=0
FAIL=0
TOTAL=0

report() {
    TOTAL=$((TOTAL + 1))
    if [ "$1" = "PASS" ]; then
        PASS=$((PASS + 1))
        echo "[PASS] $2"
    else
        FAIL=$((FAIL + 1))
        echo "[FAIL] $2 (Expected: $3, Got: $4)"
    fi
}

echo "--- Scenario 2: Auth API ---"

# 2.1 Unauthenticated access to system status
CODE=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/api/system/status)
if [ "$CODE" = "401" ] || [ "$CODE" = "403" ]; then
    report "PASS" "S2.1: Unauthenticated /api/system/status returns $CODE"
else
    report "FAIL" "S2.1: Unauthenticated /api/system/status" "401" "$CODE"
fi

# 2.2 Login as boss
LOGIN_RESP=$(curl -s https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}')
echo "  Login response: $LOGIN_RESP"
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
    report "PASS" "S2.2: Boss login returns access_token"
else
    report "FAIL" "S2.2: Boss login returns access_token" "non-empty token" "empty/missing"
fi

# 2.3 Use token to access /auth/me
ME_RESP=$(curl -s -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/auth/me)
echo "  /auth/me response: $ME_RESP"
ME_USER=$(echo "$ME_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('username',''))" 2>/dev/null)
ME_ROLE=$(echo "$ME_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('role',''))" 2>/dev/null)
if [ "$ME_USER" = "boss" ] && [ "$ME_ROLE" = "boss" ]; then
    report "PASS" "S2.3: /auth/me returns username=boss, role=boss"
else
    report "FAIL" "S2.3: /auth/me" "username=boss,role=boss" "username=$ME_USER,role=$ME_ROLE"
fi

# 2.4 Bad password
BAD_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"boss","password":"wrong"}')
if [ "$BAD_CODE" = "401" ]; then
    report "PASS" "S2.4: Bad password returns 401"
else
    report "FAIL" "S2.4: Bad password" "401" "$BAD_CODE"
fi

echo ""
echo "--- Scenario 3: Role-based Access ---"

# 3.1 Login as operator
OP_RESP=$(curl -s https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"op1","password":"test123"}')
echo "  Operator login response: $OP_RESP"
OP_TOKEN=$(echo "$OP_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [ -n "$OP_TOKEN" ] && [ "$OP_TOKEN" != "" ]; then
    report "PASS" "S3.1: Operator login returns access_token"
else
    report "FAIL" "S3.1: Operator login returns access_token" "non-empty token" "empty/missing"
fi

# 3.2 Operator tries system stop → 403
OP_STOP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer $OP_TOKEN" https://siqiangshangwu.com/api/system/stop)
if [ "$OP_STOP_CODE" = "403" ]; then
    report "PASS" "S3.2: Operator system/stop returns 403"
else
    report "FAIL" "S3.2: Operator system/stop" "403" "$OP_STOP_CODE"
fi

# 3.3 Boss tries system stop → should be allowed
BOSS_STOP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/system/stop)
if [ "$BOSS_STOP_CODE" = "200" ] || [ "$BOSS_STOP_CODE" = "202" ] || [ "$BOSS_STOP_CODE" = "204" ]; then
    report "PASS" "S3.3: Boss system/stop returns $BOSS_STOP_CODE (allowed)"
else
    report "FAIL" "S3.3: Boss system/stop" "200/202/204" "$BOSS_STOP_CODE"
fi

echo ""
echo "--- Scenario 4: SSL & Redirects ---"

# 4.1 HTTPS root
HTTPS_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/)
if [ "$HTTPS_CODE" = "200" ]; then
    report "PASS" "S4.1: HTTPS root returns 200"
else
    report "FAIL" "S4.1: HTTPS root" "200" "$HTTPS_CODE"
fi

# 4.2 HTTP redirect
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-redirs 0 http://siqiangshangwu.com/)
if [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "308" ]; then
    report "PASS" "S4.2: HTTP root redirects ($HTTP_CODE)"
else
    report "FAIL" "S4.2: HTTP root redirect" "301/302" "$HTTP_CODE"
fi

# 4.3 Health endpoint
HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/health)
if [ "$HEALTH_CODE" = "200" ]; then
    report "PASS" "S4.3: /health returns 200"
else
    report "FAIL" "S4.3: /health" "200" "$HEALTH_CODE"
fi

echo ""
echo "--- Scenario 5: Feishu Webhook ---"

FEISHU_RESP=$(curl -s https://siqiangshangwu.com/feishu/webhook -X POST -H "Content-Type: application/json" -d '{"type":"url_verification","challenge":"qa-test"}')
echo "  Feishu response: $FEISHU_RESP"
CHALLENGE=$(echo "$FEISHU_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('challenge',''))" 2>/dev/null)
if [ "$CHALLENGE" = "qa-test" ]; then
    report "PASS" "S5.1: Feishu webhook returns challenge"
else
    report "FAIL" "S5.1: Feishu webhook challenge" "qa-test" "$CHALLENGE"
fi

echo ""
echo "--- Edge Cases ---"

# E1: Empty username/password
E1_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"","password":""}')
echo "[INFO] E1: Empty creds login returns $E1_CODE"
if [ "$E1_CODE" = "400" ] || [ "$E1_CODE" = "401" ] || [ "$E1_CODE" = "422" ]; then
    report "PASS" "E1: Empty creds rejected ($E1_CODE)"
else
    report "FAIL" "E1: Empty creds" "400/401/422" "$E1_CODE"
fi

# E2: Invalid JWT token
E2_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer invalid.jwt.token" https://siqiangshangwu.com/api/auth/me)
if [ "$E2_CODE" = "401" ] || [ "$E2_CODE" = "403" ] || [ "$E2_CODE" = "422" ]; then
    report "PASS" "E2: Invalid JWT rejected ($E2_CODE)"
else
    report "FAIL" "E2: Invalid JWT" "401/403" "$E2_CODE"
fi

# E3: Non-existent API route
E3_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/nonexistent/route)
if [ "$E3_CODE" = "404" ] || [ "$E3_CODE" = "405" ]; then
    report "PASS" "E3: Non-existent route returns $E3_CODE"
else
    report "FAIL" "E3: Non-existent route" "404" "$E3_CODE"
fi

# E4: Very long username
LONG_USER=$(python3 -c "print('A'*10000)")
E4_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d "{\"username\":\"$LONG_USER\",\"password\":\"test\"}")
if [ "$E4_CODE" = "400" ] || [ "$E4_CODE" = "401" ] || [ "$E4_CODE" = "413" ] || [ "$E4_CODE" = "422" ]; then
    report "PASS" "E4: Long username rejected ($E4_CODE)"
else
    report "FAIL" "E4: Long username" "400/401/413/422" "$E4_CODE"
fi

echo ""
echo "--- Integration Test 1: Full Token Lifecycle ---"

# Login → Token → Protected → verify
INT_LOGIN=$(curl -s https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}')
INT_TOKEN=$(echo "$INT_LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
if [ -n "$INT_TOKEN" ]; then
    INT_ME_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $INT_TOKEN" https://siqiangshangwu.com/api/auth/me)
    INT_STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $INT_TOKEN" https://siqiangshangwu.com/api/system/status)
    if [ "$INT_ME_CODE" = "200" ] && [ "$INT_STATUS_CODE" = "200" ]; then
        report "PASS" "INT1: Full token lifecycle (login→me→status)"
    else
        report "FAIL" "INT1: Token lifecycle" "me=200,status=200" "me=$INT_ME_CODE,status=$INT_STATUS_CODE"
    fi
else
    report "FAIL" "INT1: Token lifecycle" "token obtained" "no token"
fi

echo ""
echo "========================================="
echo "RESULTS: $PASS/$TOTAL passed, $FAIL failed"
echo "========================================="
