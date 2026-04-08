#!/bin/bash
set -e

TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"boss","password":"test123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "=== Testing ad_monitor with dry_run=false (REAL API) ==="
RESULT=$(curl -s -X POST "http://localhost:8000/api/agents/ad_monitor/run" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}')

RUN_ID=$(echo "$RESULT" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("run_id",""))' 2>/dev/null)
echo "Run ID: $RUN_ID"

# Wait and poll
for i in 1 2 3 4 5 6; do
  sleep 10
  echo ""
  echo "=== Poll attempt $i (${i}0s elapsed) ==="
  POLL=$(curl -s "http://localhost:8000/api/agents/runs/$RUN_ID" -H "Authorization: Bearer $TOKEN")
  STATUS=$(echo "$POLL" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status","?"))' 2>/dev/null || echo "error")
  echo "Status: $STATUS"
  
  if [ "$STATUS" != "running" ]; then
    echo ""
    echo "=== Final Result ==="
    echo "$POLL" | python3 -m json.tool 2>/dev/null || echo "$POLL"
    break
  fi
done

# Also check container logs for any errors
echo ""
echo "=== Recent app logs (last 20 lines) ==="
sudo docker compose -f /opt/amazon-ai/deploy/docker/docker-compose.yml logs --tail=20 app 2>/dev/null || echo "(could not read logs)"
