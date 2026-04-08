#!/bin/bash
set -e
# Direct to backend (skip nginx SSL)
BASE="http://localhost:8000"
C="curl -s"

# Login
TOKEN=$($C -X POST "$BASE/api/auth/login" -H "Content-Type: application/json" -d '{"username":"boss","password":"test123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
echo "TOKEN_OK: ${#TOKEN} chars"

# ad_monitor dry_run=false
echo "--- ad_monitor dry_run=false ---"
RESP=$($C -X POST "$BASE/api/agents/run" -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"agent_type":"ad_monitor","params":{"campaign_id":"test","date_range":"LAST_7_DAYS","dry_run":false}}')
echo "$RESP"
RID=$(echo "$RESP" | python3 -c "import sys,json;print(json.load(sys.stdin)['run_id'])")
echo "RUN_ID: $RID"

# Poll
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  sleep 5
  R=$($C "$BASE/api/agents/runs/$RID" -H "Authorization: Bearer $TOKEN")
  S=$(echo "$R" | python3 -c "import sys,json;print(json.load(sys.stdin)['status'])")
  echo "Poll $i: $S"
  if [ "$S" = "success" ] || [ "$S" = "error" ]; then
    echo "$R" | python3 -m json.tool
    break
  fi
done

# Relevant logs
echo "--- LOGS ---"
sudo docker logs amazon-ai-app --tail 50 2>&1 | grep -i -E "ads|campaign|credential|missing|token|dry_run|error" || echo "(none)"
