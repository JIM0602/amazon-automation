#!/bin/bash
# Check env vars inside container
sudo docker exec amazon-ai-app python3 -c "
import os
for key in ['AMAZON_ADS_CLIENT_ID','AMAZON_ADS_CLIENT_SECRET','AMAZON_ADS_REFRESH_TOKEN','AMAZON_ADS_PROFILE_ID','AMAZON_ADS_REGION']:
    val = os.environ.get(key, '')
    print(f'{key}: len={len(val)} val={val[:40]}...' if len(val)>40 else f'{key}: len={len(val)} val={val}')
"
