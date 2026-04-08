#!/usr/bin/env python3
"""Check all credentials in container."""
import json
from src.config import Settings

s = Settings()

print("=== Seller Sprite ===")
print(f"  API_KEY: {s.SELLER_SPRITE_API_KEY[:10]}..." if s.SELLER_SPRITE_API_KEY else "  API_KEY: EMPTY")
print(f"  USE_MOCK: {getattr(s, 'SELLER_SPRITE_USE_MOCK', 'N/A')}")
print(f"  MCP_ENDPOINT: {getattr(s, 'SELLER_SPRITE_MCP_ENDPOINT', 'N/A')}")

print("\n=== SP-API ===")
print(f"  CLIENT_ID: {s.AMAZON_SP_API_CLIENT_ID[:20]}..." if s.AMAZON_SP_API_CLIENT_ID else "  CLIENT_ID: EMPTY")
print(f"  CLIENT_SECRET: {'SET' if s.AMAZON_SP_API_CLIENT_SECRET else 'EMPTY'}")
print(f"  REFRESH_TOKEN: {'SET' if s.AMAZON_SP_API_REFRESH_TOKEN else 'EMPTY'}")
print(f"  APP_ID: {s.AMAZON_SP_API_APP_ID[:20]}..." if getattr(s, 'AMAZON_SP_API_APP_ID', '') else "  APP_ID: EMPTY")

print("\n=== Amazon Ads ===")
print(f"  CLIENT_ID: {s.AMAZON_ADS_CLIENT_ID[:20]}..." if s.AMAZON_ADS_CLIENT_ID else "  CLIENT_ID: EMPTY")
print(f"  CLIENT_SECRET: {'SET' if s.AMAZON_ADS_CLIENT_SECRET else 'EMPTY'}")
print(f"  REFRESH_TOKEN: {'SET' if s.AMAZON_ADS_REFRESH_TOKEN else 'EMPTY'}")
print(f"  PROFILE_ID: {s.AMAZON_ADS_PROFILE_ID}" if s.AMAZON_ADS_PROFILE_ID else "  PROFILE_ID: EMPTY")

# Check how Seller Sprite client reads the API key
print("\n=== Seller Sprite Client Debug ===")
from src.seller_sprite.client import RealSellerSpriteClient
import os
os.environ['SELLER_SPRITE_USE_MOCK'] = 'false'
client = RealSellerSpriteClient()
print(f"  client.api_key: {client.api_key[:10]}..." if client.api_key else "  client.api_key: EMPTY")
print(f"  client.base_url: {getattr(client, 'base_url', 'N/A')}")

# Check how it sends the request
import inspect
# Find where it sets headers
source = inspect.getsource(client._request_json)
# Look for header-related lines
for line in source.split('\n'):
    line_stripped = line.strip()
    if 'header' in line_stripped.lower() or 'key' in line_stripped.lower() or 'auth' in line_stripped.lower() or 'secret' in line_stripped.lower():
        print(f"  CODE: {line_stripped}")
