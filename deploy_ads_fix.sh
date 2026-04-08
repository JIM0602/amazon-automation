#!/bin/bash
# 部署 Ads API v3 修复并测试
set -e

echo "=== 1. 重建 Docker 容器 ==="
cd /opt/amazon-ai
sudo docker compose -f deploy/docker/docker-compose.yml down
sudo docker compose -f deploy/docker/docker-compose.yml build --no-cache app
sudo docker compose -f deploy/docker/docker-compose.yml up -d

echo "=== 2. 等待容器启动 ==="
sleep 10

echo "=== 3. 检查容器健康 ==="
curl -s http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))"

echo ""
echo "=== 4. 获取 JWT token ==="
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token obtained: ${TOKEN:0:20}..."

echo ""
echo "=== 5. 测试 ad_monitor dry_run=false ==="
RESULT=$(curl -s -X POST http://localhost:8000/api/agents/ad_monitor/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}' \
  --max-time 120)

echo "Response:"
echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))" 2>/dev/null || echo "$RESULT"

echo ""
echo "=== 6. 检查 Docker 日志（最近 50 行）==="
sudo docker logs amazon-ai-app --tail 50 2>&1 | grep -E "(ads_api|ReportsApi|AmazonAds|ad_monitor|fetch_ad_data|reporting)" || echo "（无匹配日志）"

echo ""
echo "=== 完成 ==="
