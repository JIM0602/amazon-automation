#!/bin/bash
# Quick rebuild + direct API tests
set -e

echo "=== Step 1: Deploy updated reports.py (30min timeout) ==="
sudo docker cp /opt/amazon-ai/src/amazon_ads_api/reports.py amazon-ai-app:/app/src/amazon_ads_api/reports.py
echo "  reports.py copied into running container (no rebuild needed)"

echo ""
echo "=== Step 2: Test Seller Sprite Real API ==="
sudo docker exec amazon-ai-app python3 -c "
import os, json
os.environ['SELLER_SPRITE_USE_MOCK'] = 'false'
try:
    from src.seller_sprite.client import get_client
    client = get_client()
    print(f'Client type: {type(client).__name__}')
    result = client.search_keyword('dog leash')
    print(f'Result type: {type(result)}')
    print(f'Result keys: {list(result.keys()) if isinstance(result, dict) else \"not a dict\"}')
    print(f'Result: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}')
    print('SELLER_SPRITE: SUCCESS')
except Exception as e:
    print(f'SELLER_SPRITE: FAILED | {e}')
    import traceback; traceback.print_exc()
" 2>&1

echo ""
echo "=== Step 3: Test SP-API Token Refresh + Catalog Search ==="
sudo docker exec amazon-ai-app python3 -c "
import json
try:
    from src.amazon_sp_api.auth import SpApiAuth
    auth = SpApiAuth(dry_run=False)
    token = auth.get_access_token()
    print(f'SP-API token: {token[:20]}...')

    from src.amazon_sp_api.client import SpApiClient
    client = SpApiClient(auth=auth, dry_run=False)
    result = client.get('/catalog/2022-04-01/items', params={
        'marketplaceIds': 'ATVPDKIKX0DER',
        'keywords': 'pet fountain',
        'pageSize': '1',
    })
    print(f'Catalog result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}')
    print(f'Catalog result: {json.dumps(result, indent=2, ensure_ascii=False)[:1000]}')
    print('SP-API: SUCCESS')
except Exception as e:
    print(f'SP-API: FAILED | {e}')
    import traceback; traceback.print_exc()
" 2>&1

echo ""
echo "=== Step 4: Docker container logs (last 10 lines) ==="
sudo docker logs amazon-ai-app --tail 10 2>&1

echo ""
echo "=== DONE ==="
