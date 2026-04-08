#!/bin/bash
set -e

echo "=== Deploying ads_oauth.py, health.py, config.py fixes ==="

# 1. Backup existing files
echo "--- Backing up existing files ---"
cp /opt/amazon-ai/src/api/ads_oauth.py /opt/amazon-ai/src/api/ads_oauth.py.bak 2>/dev/null || true
cp /opt/amazon-ai/src/api/health.py /opt/amazon-ai/src/api/health.py.bak 2>/dev/null || true
cp /opt/amazon-ai/src/config.py /opt/amazon-ai/src/config.py.bak 2>/dev/null || true

# 2. Copy uploaded files
echo "--- Copying new files ---"
cp /tmp/ads_oauth.py /opt/amazon-ai/src/api/ads_oauth.py
cp /tmp/health.py /opt/amazon-ai/src/api/health.py
cp /tmp/config.py /opt/amazon-ai/src/config.py

echo "--- Files deployed ---"
echo "ads_oauth.py: $(md5sum /opt/amazon-ai/src/api/ads_oauth.py | cut -d' ' -f1)"
echo "health.py: $(md5sum /opt/amazon-ai/src/api/health.py | cut -d' ' -f1)"
echo "config.py: $(md5sum /opt/amazon-ai/src/config.py | cut -d' ' -f1)"

# 3. Rebuild Docker
echo "--- Rebuilding Docker ---"
cd /opt/amazon-ai/deploy/docker
sudo docker compose down
sudo docker compose build --no-cache app
sudo docker compose up -d

echo "--- Waiting for containers ---"
sleep 10

# 4. Verify containers
echo "--- Container status ---"
sudo docker compose ps

# 5. Quick health check
echo "--- Health check ---"
curl -s http://localhost:8000/api/health/sp-api 2>/dev/null || echo "Health check pending..."
curl -s http://localhost:8000/api/health/all 2>/dev/null || echo "Full health check pending..."

echo ""
echo "=== Deployment complete ==="
