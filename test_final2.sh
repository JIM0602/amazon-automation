#!/bin/bash
set -e
BASE="http://localhost:8000"
C="curl -s"

# Login
TOKEN=$($C -X POST "$BASE/api/auth/login" -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "TOKEN_OK: ${#TOKEN} chars"

# ad_monitor dry_run=false
echo ""
echo "=== ad_monitor dry_run=false ==="
RESP=$($C -X POST "$BASE/api/agents/ad_monitor/run" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"campaign_id":"test","date_range":"LAST_7_DAYS","dry_run":false}')
echo "Response: $RESP"
RID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['run_id'])")
echo "RUN_ID: $RID"

# Poll ad_monitor
echo ""
echo "=== Polling ad_monitor ==="
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  sleep 5
  R=$($C "$BASE/api/agents/runs/$RID" -H "Authorization: Bearer $TOKEN")
  S=$(echo "$R" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
  echo "Poll $i: $S"
  if [ "$S" = "success" ] || [ "$S" = "error" ]; then
    echo "$R" | python3 -m json.tool 2>/dev/null || echo "$R"
    break
  fi
done

# Relevant logs
echo ""
echo "=== Container logs (ads-related) ==="
sudo docker logs amazon-ai-app --tail 80 2>&1 | grep -i -E "ads|campaign|credential|missing|token|dry_run|error|auth|refresh" | tail -30 || echo "(none)"

echo ""
echo "=== ALL 11 AGENTS dry_run=true ==="
AGENTS="selection listing competitor persona ad_monitor brand_planning whitepaper image_generation inventory core_management product_listing"
RIDS=""
for agent in $AGENTS; do
  RESP=$($C -X POST "$BASE/api/agents/$agent/run" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"dry_run":true}')
  RID2=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin).get('run_id','FAIL'))" 2>/dev/null || echo "FAIL")
  echo "  $agent -> $RID2"
  RIDS="$RIDS $agent:$RID2"
done

echo ""
echo "=== Polling all agents (wait 15s then check) ==="
sleep 15
PASS=0
FAIL=0
for entry in $RIDS; do
  agent=$(echo "$entry" | cut -d: -f1)
  rid=$(echo "$entry" | cut -d: -f2)
  if [ "$rid" = "FAIL" ]; then
    echo "  ❌ $agent: FAILED to start"
    FAIL=$((FAIL+1))
    continue
  fi
  R=$($C "$BASE/api/agents/runs/$rid" -H "Authorization: Bearer $TOKEN")
  S=$(echo "$R" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
  if [ "$S" = "success" ]; then
    echo "  ✅ $agent: SUCCESS"
    PASS=$((PASS+1))
  elif [ "$S" = "running" ] || [ "$S" = "pending" ]; then
    echo "  ⏳ $agent: $S (still running)"
  else
    echo "  ❌ $agent: $S"
    FAIL=$((FAIL+1))
  fi
done

# Second poll for any still running
sleep 10
echo ""
echo "=== Second poll ==="
for entry in $RIDS; do
  agent=$(echo "$entry" | cut -d: -f1)
  rid=$(echo "$entry" | cut -d: -f2)
  if [ "$rid" = "FAIL" ]; then continue; fi
  R=$($C "$BASE/api/agents/runs/$rid" -H "Authorization: Bearer $TOKEN")
  S=$(echo "$R" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
  if [ "$S" = "success" ]; then
    echo "  ✅ $agent"
  else
    echo "  ❌ $agent: $S"
  fi
done

echo ""
echo "=== Health check ==="
$C "$BASE/health" | python3 -m json.tool

echo ""
echo "=== DONE ==="
