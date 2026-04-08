#!/bin/bash
# Rebuild Docker + test APIs with correct credentials
set -e

echo "=== Step 1: Rebuild Docker (picks up new .env with SELLER_SPRITE_USE_MOCK=false) ==="
cd /opt/amazon-ai
sudo docker compose -f deploy/docker/docker-compose.yml down
sudo docker compose -f deploy/docker/docker-compose.yml build
sudo docker compose -f deploy/docker/docker-compose.yml up -d

echo ""
echo "=== Step 2: Wait for healthy ==="
for i in $(seq 1 30); do
  STATUS=$(sudo docker inspect --format='{{.State.Health.Status}}' amazon-ai-app 2>/dev/null || echo "starting")
  echo "  [$i/30] Status: $STATUS"
  if [ "$STATUS" = "healthy" ]; then
    echo "  Container healthy!"
    break
  fi
  sleep 5
done

echo ""
echo "=== Step 3: Verify env vars in container ==="
sudo docker exec amazon-ai-app python3 -c "
from src.config import Settings
s = Settings()
print(f'SELLER_SPRITE_USE_MOCK = {s.SELLER_SPRITE_USE_MOCK}')
print(f'SELLER_SPRITE_API_KEY = {s.SELLER_SPRITE_API_KEY[:10]}...')
print(f'SP_CLIENT_ID = {s.AMAZON_SP_API_CLIENT_ID[:20]}...')
print(f'SP_SECRET = {bool(s.AMAZON_SP_API_CLIENT_SECRET)}')
print(f'SP_REFRESH = {bool(s.AMAZON_SP_API_REFRESH_TOKEN)}')
"

echo ""
echo "=== Step 4: Test Seller Sprite REST API ==="
sudo docker exec amazon-ai-app python3 -c "
import json
from src.config import Settings
s = Settings()
print(f'USE_MOCK from Settings: {s.SELLER_SPRITE_USE_MOCK}')

# Direct HTTP call to check what Seller Sprite returns
import httpx
url = 'https://api.sellersprite.com/v1/market/research'
headers = {'secret-key': s.SELLER_SPRITE_API_KEY}
params = {'marketplace': 'US', 'keyword': 'dog leash', 'month': '2026-03'}
print(f'Request: GET {url}')
print(f'Headers: secret-key={s.SELLER_SPRITE_API_KEY[:10]}...')
try:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url, headers=headers, params=params)
    print(f'Status: {resp.status_code}')
    print(f'Response: {resp.text[:1000]}')
except Exception as e:
    print(f'Error: {e}')

# Also try POST
print()
url2 = 'https://api.sellersprite.com/v1/keyword/research'
print(f'Request: POST {url2}')
try:
    with httpx.Client(timeout=30.0) as client:
        resp2 = client.post(url2, headers=headers, json={'marketplace': 'US', 'keyword': 'dog leash'})
    print(f'Status: {resp2.status_code}')
    print(f'Response: {resp2.text[:1000]}')
except Exception as e:
    print(f'Error: {e}')
" 2>&1

echo ""
echo "=== Step 5: Test SP-API with credentials from Settings ==="
sudo docker exec amazon-ai-app python3 -c "
import json
from src.config import Settings
s = Settings()

from src.amazon_sp_api.auth import SpApiAuth
auth = SpApiAuth(
    client_id=s.AMAZON_SP_API_CLIENT_ID,
    client_secret=s.AMAZON_SP_API_CLIENT_SECRET,
    refresh_token=s.AMAZON_SP_API_REFRESH_TOKEN,
    dry_run=False,
)
token = auth.get_access_token()
print(f'SP-API token: {token[:20]}...')

from src.amazon_sp_api.client import SpApiClient
client = SpApiClient(auth=auth, dry_run=False)
try:
    result = client.get('/catalog/2022-04-01/items', params={
        'marketplaceIds': 'ATVPDKIKX0DER',
        'keywords': 'pet fountain',
        'pageSize': '1',
    })
    print(f'Catalog result type: {type(result)}')
    if isinstance(result, dict):
        print(f'Keys: {list(result.keys())}')
        items = result.get('items', [])
        print(f'Items count: {len(items)}')
        if items:
            print(f'First item: {json.dumps(items[0], indent=2, ensure_ascii=False)[:500]}')
    print('SP-API: SUCCESS')
except Exception as e:
    print(f'SP-API catalog error: {e}')
    import traceback; traceback.print_exc()
" 2>&1

echo ""
echo "=== Step 6: Copy updated reports.py into container ==="
sudo docker cp /opt/amazon-ai/src/amazon_ads_api/reports.py amazon-ai-app:/app/src/amazon_ads_api/reports.py
echo "  Done - reports.py with 30min timeout deployed"

echo ""
echo "=== ALL TESTS DONE ==="
