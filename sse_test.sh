#!/bin/bash
TOKEN=$(python3 /tmp/get_token.py 2>/dev/null)
echo "Token: ${TOKEN:0:20}..."
echo ""
echo "=== SSE core_management ==="
curl -s -N --max-time 10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"hello SSE test"}' \
  http://localhost:8000/api/chat/core_management/stream 2>&1 | head -20
echo ""
echo "=== SSE brand_planning ==="
curl -s -N --max-time 10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"hello SSE test"}' \
  http://localhost:8000/api/chat/brand_planning/stream 2>&1 | head -20
echo ""
echo "=== SSE no auth ==="
curl -s --max-time 5 \
  -H "Content-Type: application/json" \
  -d '{"message":"no auth test"}' \
  -o /dev/null -w "HTTP Status: %{http_code}\nContent-Type: %{content_type}" \
  http://localhost:8000/api/chat/core_management/stream
echo ""
