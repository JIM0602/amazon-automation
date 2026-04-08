#!/bin/bash
set -e

# Login and get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"boss","password":"test123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "=== TOKEN obtained ==="

# Health check
echo "=== Health Check ==="
curl -s http://localhost:8000/api/health -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Agent types
echo ""
echo "=== Agent Types ==="
curl -s http://localhost:8000/api/agents/types -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Test all 11 agents with dry_run=true
AGENTS=("selection" "listing" "competitor" "persona" "ad_monitor" "brand_planning" "whitepaper" "image_generation" "inventory" "core_management" "product_listing")

echo ""
echo "=== Testing All 11 Agents (dry_run=true) ==="
for agent in "${AGENTS[@]}"; do
  echo ""
  echo "--- Testing: $agent ---"
  RESULT=$(curl -s -w "\n%{http_code}" -X POST "http://localhost:8000/api/agents/$agent/run" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"dry_run": true}')
  
  HTTP_CODE=$(echo "$RESULT" | tail -n1)
  BODY=$(echo "$RESULT" | sed '$d')
  
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
    echo "  ✅ $agent — HTTP $HTTP_CODE"
    # Show status from response
    echo "  $(echo $BODY | python3 -c 'import sys,json; d=json.load(sys.stdin); print(f"status={d.get(\"status\",\"?\")}, run_id={d.get(\"run_id\",\"?\")}")' 2>/dev/null || echo "$BODY" | head -c 200)"
  else
    echo "  ❌ $agent — HTTP $HTTP_CODE"
    echo "  $BODY" | head -c 300
  fi
done

echo ""
echo "=== All Agent Tests Complete ==="
