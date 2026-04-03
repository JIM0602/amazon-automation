#!/bin/bash
# Debug S3.3: Boss system/stop
TOKEN=$(curl -s https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

echo "=== Boss stop with no body ==="
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/system/stop

echo ""
echo "=== Boss stop with empty JSON body ==="
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}' https://siqiangshangwu.com/api/system/stop

echo ""
echo "=== Boss stop with reason ==="
curl -s -w "\nHTTP_CODE: %{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"reason":"qa-test"}' https://siqiangshangwu.com/api/system/stop

echo ""
echo "=== Check API docs/routes ==="
curl -s -w "\nHTTP_CODE: %{http_code}\n" https://siqiangshangwu.com/docs 2>/dev/null | head -5
curl -s -o /dev/null -w "openapi.json: %{http_code}\n" https://siqiangshangwu.com/openapi.json
