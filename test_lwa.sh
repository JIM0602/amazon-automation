#!/bin/bash
# Test LWA token refresh directly
echo "=== Testing Amazon LWA token refresh ==="
RESP=$(curl -s -X POST https://api.amazon.com/auth/o2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token&client_id=$(sudo docker exec amazon-ai-app python3 -c 'import os;print(os.environ.get("AMAZON_ADS_CLIENT_ID",""))')&client_secret=$(sudo docker exec amazon-ai-app python3 -c 'import os;print(os.environ.get("AMAZON_ADS_CLIENT_SECRET",""))')&refresh_token=$(sudo docker exec amazon-ai-app python3 -c 'import os;print(os.environ.get("AMAZON_ADS_REFRESH_TOKEN",""))')")
echo "Response: $RESP"
echo ""
echo "=== Also test SP-API token refresh ==="
RESP2=$(curl -s -X POST https://api.amazon.com/auth/o2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token&client_id=$(sudo docker exec amazon-ai-app python3 -c 'import os;print(os.environ.get("AMAZON_SP_API_CLIENT_ID",""))')&client_secret=$(sudo docker exec amazon-ai-app python3 -c 'import os;print(os.environ.get("AMAZON_SP_API_CLIENT_SECRET",""))')&refresh_token=$(sudo docker exec amazon-ai-app python3 -c 'import os;print(os.environ.get("AMAZON_SP_API_REFRESH_TOKEN",""))')")
echo "Response: $RESP2"
