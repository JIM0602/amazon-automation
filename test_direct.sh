#!/bin/bash
sudo docker exec amazon-ai-app python3 -c "
import os, sys, traceback
os.environ.setdefault('DATABASE_URL', 'postgresql://app_user:changeme@postgres:5432/amazon_ai')

agents = [
    ('selection', lambda: __import__('src.agents.selection_agent', fromlist=['run']).run(category='pet_supplies', dry_run=True)),
    ('listing', lambda: __import__('src.agents.listing_agent', fromlist=['run']).run(asin='', product_name='', category='', dry_run=True)),
    ('competitor', lambda: __import__('src.agents.competitor_agent', fromlist=['execute']).execute(target_asin='', competitor_asins=[], dry_run=True)),
    ('persona', lambda: __import__('src.agents.persona_agent', fromlist=['execute']).execute(category='', asin='', dry_run=True)),
    ('ad_monitor', lambda: __import__('src.agents.ad_monitor_agent', fromlist=['execute']).execute(campaigns=[], thresholds={}, dry_run=True)),
    ('brand_planning', lambda: __import__('src.agents.brand_planning_agent.agent', fromlist=['execute']).execute(brand_name='', category='', target_market='US', budget_range='', dry_run=True)),
    ('whitepaper', lambda: __import__('src.agents.whitepaper_agent.agent', fromlist=['execute']).execute(product_name='', asin='', category='', target_audience='', dry_run=True)),
    ('image_generation', lambda: __import__('src.agents.image_gen_agent', fromlist=['execute']).execute(prompt='test', product_name=None, style='professional', size='1024x1024', dry_run=True)),
    ('inventory', lambda: __import__('src.agents.inventory_agent', fromlist=['execute']).execute(sku_list=[], threshold_days=30, dry_run=True)),
    ('core_management', lambda: __import__('src.agents.core_agent', fromlist=['execute']).execute(report_type='daily', dry_run=True)),
]

for name, fn in agents:
    try:
        result = fn()
        keys = list(result.keys())[:5] if isinstance(result, dict) else str(type(result))
        status = result.get('status', '?') if isinstance(result, dict) else '?'
        print(f'{name:20s} | OK | status={status} | keys={keys}')
    except Exception as e:
        traceback.print_exc()
        print(f'{name:20s} | FAILED | {e}')
    print()
" 2>&1
