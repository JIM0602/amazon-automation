#!/bin/bash
# 验证 Seller Sprite API 和 SP-API 真实调用
set -e

echo "=== 1. 获取 JWT token ==="
TOKEN=$(curl -s -X POST http://localhost:8000/api/agents/ad_monitor/run 2>/dev/null | head -1)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"boss","password":"test123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:20}..."

echo ""
echo "=== 2. 测试 Seller Sprite (selection agent, dry_run=false) ==="
echo "  调用 selection agent 会使用 Seller Sprite API..."
RESULT=$(curl -s -X POST http://localhost:8000/api/agents/selection/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "keyword": "dog leash", "market": "US"}' \
  --max-time 120)
echo "Selection Response:"
echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))" 2>/dev/null || echo "$RESULT"

echo ""
echo "=== 3. Seller Sprite 相关日志 ==="
sudo docker logs amazon-ai-app --tail 30 2>&1 | grep -iE "(seller_sprite|sellersprite|selection)" || echo "（无匹配日志）"

echo ""
echo "=== 4. 直接测试 Seller Sprite API ==="
# 直接在容器内测试 Seller Sprite REST API
sudo docker exec amazon-ai-app python3 -c "
import os
os.environ.setdefault('SELLER_SPRITE_USE_MOCK', 'false')
try:
    from src.seller_sprite.client import RealSellerSpriteClient
    client = RealSellerSpriteClient()
    print(f'API Key configured: {bool(client.api_key)}')
    print(f'API Key prefix: {(client.api_key or \"\")[:8]}...')
    result = client.search_keyword('dog leash')
    print(f'SUCCESS: search_keyword returned: keyword={result.get(\"keyword\")}, volume={result.get(\"search_volume\")}')
except Exception as e:
    print(f'ERROR: {e}')
"

echo ""
echo "=== 5. 直接测试 SP-API token refresh + catalog call ==="
sudo docker exec amazon-ai-app python3 -c "
try:
    from src.amazon_sp_api.auth import SpApiAuth
    auth = SpApiAuth(dry_run=False)
    token = auth.get_access_token()
    print(f'SP-API token refresh SUCCESS: {token[:20]}...')

    from src.amazon_sp_api.client import SpApiClient
    client = SpApiClient(auth=auth, dry_run=False)
    # 尝试获取 catalog 数据（只读）
    try:
        result = client.get('/catalog/2022-04-01/items', params={
            'marketplaceIds': 'ATVPDKIKX0DER',
            'keywords': 'pet fountain',
            'pageSize': '1',
        })
        print(f'SP-API catalog call SUCCESS: {str(result)[:200]}')
    except Exception as e2:
        print(f'SP-API catalog call failed (may need specific permissions): {e2}')
except Exception as e:
    print(f'SP-API auth ERROR: {e}')
"

echo ""
echo "=== 完成 ==="
