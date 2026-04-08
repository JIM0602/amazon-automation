#!/bin/bash
# Final verification script
echo "=== F1: Container Health ==="
sudo docker ps --format 'table {{.Names}}\t{{.Status}}'
echo ""

echo "=== F2: Health Endpoints ==="
curl -s http://localhost:8000/api/health/all | python3 -m json.tool
echo ""

echo "=== F3: Agent Types ==="
curl -s http://localhost:8000/api/agents/types | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data['types']:
    print(f\"  {t['type']:20s} | {t['name']}\")
"
echo ""

echo "=== F4: Frontend Check ==="
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/)
echo "Frontend HTTP: $HTTP_CODE"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' https://siqiangshangwu.com/)
echo "HTTPS site: $HTTP_CODE"
echo ""

echo "=== F5: Recent Successful Runs ==="
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login -H 'Content-Type: application/json' -d '{"username":"boss","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s "http://localhost:8000/api/agents/runs?status=success&limit=11" -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"  Total successful runs: {data['total']}\")
for r in data['runs']:
    agent = r.get('agent_type','?')
    started = r.get('started_at','?')[:19]
    finished = (r.get('finished_at') or 'N/A')[:19]
    print(f'  {agent:20s} | {started} | {finished}')
"
echo ""

echo "=== F6: Knowledge Base Document Count ==="
sudo docker exec amazon-ai-app python3 -c "
from src.db.connection import get_session_local
from src.db.models import Document
db = get_session_local()()
total = db.query(Document).count()
print(f'  Documents in KB: {total}')
db.close()
" 2>&1 | grep -v Warning | grep -v warn

echo ""
echo "=== VERIFICATION COMPLETE ==="
