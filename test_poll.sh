#!/bin/bash
set -e

TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"boss","password":"test123"}' | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# Check health at different paths
echo "=== Trying health paths ==="
for path in "/api/health" "/health" "/api/health/"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000$path" -H "Authorization: Bearer $TOKEN")
  echo "  $path -> HTTP $CODE"
done

# Poll all 11 agent runs
RUNS=(
  "b8b1ff53-1078-42cd-90a8-1f4c79afd719"
  "43bef042-0202-4fbb-9550-9db2e25b434d"
  "8d4fffc5-9251-4ce5-b6fd-658283f6a5ad"
  "cbf6132c-e05f-4c93-a371-3d0f6f0bf914"
  "54c5afc1-9399-420a-aff9-0e5239a9fb84"
  "7ff513e3-818b-49e4-94cc-1a228e4db247"
  "51bb3bf5-717f-48a2-91af-ad0e8e588ccc"
  "97f72d14-cb48-4282-ba70-e9a3dce54423"
  "d07e7ff8-b119-4b52-b021-8b073d2fa30a"
  "efb06f76-b03f-4dfa-a078-014afa9e6051"
  "62935161-3556-4bfd-a72e-e8be246814b8"
)
NAMES=("selection" "listing" "competitor" "persona" "ad_monitor" "brand_planning" "whitepaper" "image_generation" "inventory" "core_management" "product_listing")

echo ""
echo "=== Agent Run Results ==="
for i in "${!RUNS[@]}"; do
  RESULT=$(curl -s "http://localhost:8000/api/agents/runs/${RUNS[$i]}" -H "Authorization: Bearer $TOKEN")
  STATUS=$(echo "$RESULT" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("status","?"))' 2>/dev/null || echo "error")
  if [ "$STATUS" = "success" ]; then
    echo "  ✅ ${NAMES[$i]} — $STATUS"
  elif [ "$STATUS" = "running" ]; then
    echo "  ⏳ ${NAMES[$i]} — $STATUS (still running)"
  else
    echo "  ❌ ${NAMES[$i]} — $STATUS"
    echo "     $(echo $RESULT | head -c 300)"
  fi
done
