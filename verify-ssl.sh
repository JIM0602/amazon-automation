#!/bin/bash
echo "=========================================="
echo " PUDIWIND AI — SSL 部署完整验证"
echo "=========================================="

echo ""
echo "=== 1. HTTPS 主页 (期望 200) ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/)
echo "Status: $STATUS"

echo ""
echo "=== 2. HTTP → HTTPS 重定向 (期望 301) ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://siqiangshangwu.com/)
echo "Status: $STATUS"

echo ""
echo "=== 3. HTTPS /health (期望 200) ==="
HEALTH=$(curl -s https://siqiangshangwu.com/health)
echo "Response: $HEALTH"

echo ""
echo "=== 4. HTTPS /api/auth/me 无认证 (期望 401) ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/api/auth/me)
echo "Status: $STATUS"

echo ""
echo "=== 5. HTTPS 登录 API ==="
LOGIN=$(curl -s https://siqiangshangwu.com/api/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"test123"}')
echo "Response: $(echo $LOGIN | head -c 120)..."
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token','FAIL'))" 2>/dev/null)
echo "Token: ${TOKEN:0:50}..."

echo ""
echo "=== 6. HTTPS /api/auth/me 有认证 (期望 200) ==="
ME=$(curl -s -H "Authorization: Bearer $TOKEN" https://siqiangshangwu.com/api/auth/me)
echo "Response: $ME"

echo ""
echo "=== 7. HTTPS /api/system/status 无认证 (期望 401) ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/api/system/status)
echo "Status: $STATUS"

echo ""
echo "=== 8. 飞书 Webhook (期望 challenge 回显) ==="
FEISHU=$(curl -s https://siqiangshangwu.com/feishu/webhook -X POST \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"ssl-test-ok"}')
echo "Response: $FEISHU"

echo ""
echo "=== 9. Login 页面 (期望 200) ==="
STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://siqiangshangwu.com/login)
echo "Status: $STATUS"

echo ""
echo "=== 10. SSL 证书信息 ==="
echo | openssl s_client -connect siqiangshangwu.com:443 -servername siqiangshangwu.com 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null

echo ""
echo "=========================================="
echo " 验证完成"
echo "=========================================="
