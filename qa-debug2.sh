#!/bin/bash
echo "=== Debug S3.3: System state ==="
TOKEN=$(curl -s https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

echo "--- Current system status ---"
curl -s -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/system/status
echo ""

echo "--- Try system start first ---"
curl -s -w "\nHTTP: %{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"reason":"qa-restart"}' https://siqiangshangwu.com/api/system/start
echo ""

echo "--- System status after start ---"
curl -s -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/system/status
echo ""

echo "--- Now try stop again ---"
curl -s -w "\nHTTP: %{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"reason":"qa-test-verify"}' https://siqiangshangwu.com/api/system/stop
echo ""

echo "--- Restart system to clean state ---"
curl -s -w "\nHTTP: %{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"reason":"qa-cleanup"}' https://siqiangshangwu.com/api/system/start
echo ""

echo "--- Final status ---"
curl -s -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/system/status
echo ""
