#!/bin/bash
set -e

echo "=== Phase 3b Deploy: Creating directories ==="
mkdir -p /opt/amazon-ai/src/amazon_ads_api
mkdir -p /opt/amazon-ai/src/agents/product_listing_agent

echo "=== Phase 3b Deploy: Files already uploaded via scp ==="
echo "Verifying files exist..."

FILES=(
  "/opt/amazon-ai/src/amazon_ads_api/__init__.py"
  "/opt/amazon-ai/src/amazon_ads_api/auth.py"
  "/opt/amazon-ai/src/amazon_ads_api/client.py"
  "/opt/amazon-ai/src/amazon_ads_api/campaigns.py"
  "/opt/amazon-ai/src/amazon_ads_api/reports.py"
  "/opt/amazon-ai/src/agents/product_listing_agent/__init__.py"
  "/opt/amazon-ai/src/agents/product_listing_agent/schemas.py"
  "/opt/amazon-ai/src/agents/product_listing_agent/nodes.py"
  "/opt/amazon-ai/src/agents/product_listing_agent/agent.py"
  "/opt/amazon-ai/src/agents/ad_monitor_agent/nodes.py"
  "/opt/amazon-ai/src/api/agents.py"
  "/opt/amazon-ai/src/amazon_sp_api/listings.py"
  "/opt/amazon-ai/src/amazon_sp_api/client.py"
  "/opt/amazon-ai/src/amazon_sp_api/__init__.py"
)

MISSING=0
for f in "${FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "MISSING: $f"
    MISSING=$((MISSING + 1))
  else
    echo "OK: $f"
  fi
done

if [ $MISSING -gt 0 ]; then
  echo "ERROR: $MISSING files missing!"
  exit 1
fi

echo "=== All 14 files verified ==="

echo "=== Rebuilding Docker ==="
cd /opt/amazon-ai/deploy/docker
sudo docker compose down
sudo docker compose build --no-cache
sudo docker compose up -d

echo "=== Waiting for containers to start ==="
sleep 10

echo "=== Checking container status ==="
sudo docker compose ps

echo "=== Checking app logs (last 30 lines) ==="
sudo docker compose logs --tail=30 app

echo "=== Phase 3b Deploy COMPLETE ==="
