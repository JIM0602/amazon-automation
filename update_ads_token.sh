#!/bin/bash
# Update AMAZON_ADS_REFRESH_TOKEN in .env and rebuild Docker
set -e

echo "=== Updating AMAZON_ADS_REFRESH_TOKEN ==="

# Use python3 with heredoc to safely handle pipe character in token
python3 << 'PYEOF'
import re

env_file = "/opt/amazon-ai/.env"
new_token = "Atzr|IwEBIBLQI941sd1QokrTFK4K48dpWqX1xh6JIbS9DR-i3Fmo3AXLbS4QT9Q-h_GSudQvSLH2j5FwDIgdyA7ikc7UpOM-aVWFE_X2hpFA3vz7kgEQewyRcuUf5yO1l3sWMhQehjN_8yQQBI1c-c-tJZVdqXcwquFc25k9264jMyzY5WjIBxoCXCOiKnrQDYBTSQK8d_wmoVJopzhVsG-anLkM4SKIBmxLp7vby5fEQpmcWqHDyTyScb-2JwnyBH5vEPSRkCFoudEfU0oIacsW9e1XFqNbW3JjaeK9XsVVn9RafNl0oTaw0z78Bx31D3v1LYNEztB4uxt_dFjaOZCsbNgD5H0hdcWLc4wRRrp9Hko9aLq25D1WCh01T2sJ-Qgja8Lf3T1ABbUJJ44jbEt6PGMPHjS6U5FSfiishSzHjLVsBDqKGpeeak_T9tnEOhX9Ry5QvD7m8TlbnjFFIZNrpBrL8CsqYDP603yYkBPaYSNJQxHSjT-ATy2dRcsxs-DNlFHW3vrlOq5w5uWg8z_pLBYME_Eq"

with open(env_file, "r") as f:
    content = f.read()

if "AMAZON_ADS_REFRESH_TOKEN=" in content:
    content = re.sub(r'^AMAZON_ADS_REFRESH_TOKEN=.*$', f'AMAZON_ADS_REFRESH_TOKEN={new_token}', content, flags=re.MULTILINE)
    print("Replaced existing AMAZON_ADS_REFRESH_TOKEN")
else:
    content = content.rstrip('\n') + f'\nAMAZON_ADS_REFRESH_TOKEN={new_token}\n'
    print("Appended AMAZON_ADS_REFRESH_TOKEN")

with open(env_file, "w") as f:
    f.write(content)

# Verify
with open(env_file, "r") as f:
    for line in f:
        if line.startswith("AMAZON_ADS_REFRESH_TOKEN="):
            print(f"Verified: {line[:80]}...")
            break
PYEOF

echo ""
echo "=== Rebuilding Docker ==="
cd /opt/amazon-ai/deploy/docker
sudo docker compose down
sudo docker compose build
sudo docker compose up -d

echo ""
echo "=== Waiting for containers to start (15s) ==="
sleep 15

echo "=== Container status ==="
sudo docker compose ps

echo ""
echo "=== Health check ==="
curl -s http://localhost:8000/health
echo ""

echo "=== Verifying token in container ==="
sudo docker exec amazon-ai-app printenv AMAZON_ADS_REFRESH_TOKEN | cut -c1-80
echo "..."
echo ""
echo "=== DONE ==="
