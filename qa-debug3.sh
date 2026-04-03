#!/bin/bash
TOKEN=$(curl -s https://siqiangshangwu.com/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

echo "--- Try DELETE on system/stop ---"
curl -s -w "\nHTTP: %{http_code}\n" -X DELETE -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/system/stop
echo ""

echo "--- Try POST on system/resume ---"
curl -s -w "\nHTTP: %{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"reason":"qa-resume"}' https://siqiangshangwu.com/api/system/resume
echo ""

echo "--- Try POST on system/restart ---"
curl -s -w "\nHTTP: %{http_code}\n" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"reason":"qa-restart"}' https://siqiangshangwu.com/api/system/restart
echo ""

echo "--- openapi spec for system endpoints ---"
curl -s https://siqiangshangwu.com/openapi.json | python3 -c "
import sys,json
spec = json.load(sys.stdin)
for path, methods in spec.get('paths',{}).items():
    if 'system' in path:
        for method in methods:
            print(f'{method.upper()} {path}')
" 2>/dev/null

echo ""
echo "--- Final status ---"
curl -s -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/system/status
echo ""
