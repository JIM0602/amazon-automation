#!/bin/bash
set -e

BASE="https://localhost"
CURL="curl -s --insecure"

echo "=== Step 1: Login ==="
TOKEN=$($CURL -X POST "$BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:20}..."

echo ""
echo "=== Step 2: Test ad_monitor dry_run=false ==="
AD_RESP=$($CURL -X POST "$BASE/api/agents/run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"agent_type":"ad_monitor","params":{"campaign_id":"test","date_range":"LAST_7_DAYS","dry_run":false}}')
echo "Response: $AD_RESP"
AD_RUN_ID=$(echo "$AD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['run_id'])")
echo "Run ID: $AD_RUN_ID"

echo ""
echo "=== Step 3: Poll ad_monitor result (up to 60s) ==="
for i in $(seq 1 12); do
  sleep 5
  RESULT=$($CURL "$BASE/api/agents/runs/$AD_RUN_ID" \
    -H "Authorization: Bearer $TOKEN")
  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "  Poll $i: status=$STATUS"
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "error" ]; then
    echo "  Final result:"
    echo "$RESULT" | python3 -m json.tool
    break
  fi
done

echo ""
echo "=== Step 4: Check container logs for Ads API calls ==="
sudo docker logs amazon-ai-app --tail 30 2>&1 | grep -i -E "ads|campaign|auth|token|credential|missing|error" || echo "(no matching log lines)"

echo ""
echo "=== Step 5: Run ALL 11 agents dry_run=true ==="
AGENTS=("selection" "listing" "competitor" "persona" "ad_monitor" "brand_planning" "whitepaper" "image_generation" "inventory" "core_management" "product_listing")
declare -A RUN_IDS

for agent in "${AGENTS[@]}"; do
  RESP=$($CURL -X POST "$BASE/api/agents/run" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d "{\"agent_type\":\"$agent\",\"params\":{\"dry_run\":true}}")
  RID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('run_id','FAIL'))" 2>/dev/null || echo "FAIL")
  echo "  $agent -> run_id=$RID"
  RUN_IDS[$agent]=$RID
done

echo ""
echo "=== Step 6: Poll all 11 agents (up to 90s) ==="
sleep 10
ALL_DONE=0
for attempt in $(seq 1 8); do
  ALL_DONE=1
  for agent in "${AGENTS[@]}"; do
    RID=${RUN_IDS[$agent]}
    if [ "$RID" = "FAIL" ]; then
      continue
    fi
    RESULT=$($CURL "$BASE/api/agents/runs/$RID" \
      -H "Authorization: Bearer $TOKEN")
    STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
    if [ "$STATUS" != "success" ] && [ "$STATUS" != "error" ]; then
      ALL_DONE=0
    fi
    echo "  [$attempt] $agent: $STATUS"
  done
  if [ $ALL_DONE -eq 1 ]; then
    echo "  All agents completed!"
    break
  fi
  sleep 10
done

echo ""
echo "=== Step 7: Final status summary ==="
PASS=0
FAIL=0
for agent in "${AGENTS[@]}"; do
  RID=${RUN_IDS[$agent]}
  if [ "$RID" = "FAIL" ]; then
    echo "  ❌ $agent: FAILED to start"
    FAIL=$((FAIL+1))
    continue
  fi
  RESULT=$($CURL "$BASE/api/agents/runs/$RID" \
    -H "Authorization: Bearer $TOKEN")
  STATUS=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
  if [ "$STATUS" = "success" ]; then
    echo "  ✅ $agent: SUCCESS"
    PASS=$((PASS+1))
  else
    echo "  ❌ $agent: $STATUS"
    FAIL=$((FAIL+1))
  fi
done
echo ""
echo "=== TOTAL: $PASS passed, $FAIL failed out of 11 ==="

echo ""
echo "=== Step 8: Health check ==="
$CURL "$BASE/health" | python3 -m json.tool

echo ""
echo "=== DONE ==="
