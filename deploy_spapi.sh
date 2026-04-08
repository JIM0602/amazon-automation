#!/bin/bash
# Add SP-API credentials to .env
# Check if SP-API vars already exist
if grep -q "AMAZON_SP_API_CLIENT_ID" /opt/amazon-ai/.env; then
    echo "SP-API vars already exist, updating..."
    sed -i 's/^AMAZON_SP_API_CLIENT_ID=.*/AMAZON_SP_API_CLIENT_ID=amzn1.application-oa2-client.b7d5e5e937224b71ae06f459b43b5a91/' /opt/amazon-ai/.env
    sed -i 's/^AMAZON_SP_API_CLIENT_SECRET=.*/AMAZON_SP_API_CLIENT_SECRET=amzn1.oa2-cs.v1.8a2098728a33e22f2d8c5d4b3a07019b7676ec5efa9f229e4a467310d85941bc/' /opt/amazon-ai/.env
    sed -i 's/^AMAZON_SP_API_APP_ID=.*/AMAZON_SP_API_APP_ID=amzn1.sp.solution.42229d18-c394-4688-af53-8bb25337c433/' /opt/amazon-ai/.env
    sed -i "s|^AMAZON_SP_API_REFRESH_TOKEN=.*|AMAZON_SP_API_REFRESH_TOKEN=Atzr\|IwEBILCfY_YfyIUJvFRN8CWmdRZRUEHofQgn0YyfbyZUz6iq7xVQkOPUlf5KUpmnR6vcutNwOB-M7xbn9VjonzUawopsLqwf8TelrvlgavcgsIzrFHakRq-2mZV_IreZjHN5B8Bm5elxgqtqPRm1e7qMrwzfW78ASiYn5Zl-pP6TzsHOld_kuBaEEN9Pqj8mHjjBXX3PYFohuH-RXV_J8nm78lAWqT0kDdhaHHssIjbQkFdHtZ4_JGAtUxvphiod34bfJ7lTCWU8xb0e1oN4Bhgo_CwiV4IcyfupYgqdfOIyuZau_QZkHM-tsoKwE_wCAUpqQ0t8SzvIWb1KBLQf_G113S93|" /opt/amazon-ai/.env
else
    echo "Adding SP-API vars..."
    cat >> /opt/amazon-ai/.env << 'SPEOF'
AMAZON_SP_API_CLIENT_ID=amzn1.application-oa2-client.b7d5e5e937224b71ae06f459b43b5a91
AMAZON_SP_API_CLIENT_SECRET=amzn1.oa2-cs.v1.8a2098728a33e22f2d8c5d4b3a07019b7676ec5efa9f229e4a467310d85941bc
AMAZON_SP_API_APP_ID=amzn1.sp.solution.42229d18-c394-4688-af53-8bb25337c433
SPEOF
    # Refresh token contains pipe character, use different approach
    echo 'AMAZON_SP_API_REFRESH_TOKEN=Atzr|IwEBILCfY_YfyIUJvFRN8CWmdRZRUEHofQgn0YyfbyZUz6iq7xVQkOPUlf5KUpmnR6vcutNwOB-M7xbn9VjonzUawopsLqwf8TelrvlgavcgsIzrFHakRq-2mZV_IreZjHN5B8Bm5elxgqtqPRm1e7qMrwzfW78ASiYn5Zl-pP6TzsHOld_kuBaEEN9Pqj8mHjjBXX3PYFohuH-RXV_J8nm78lAWqT0kDdhaHHssIjbQkFdHtZ4_JGAtUxvphiod34bfJ7lTCWU8xb0e1oN4Bhgo_CwiV4IcyfupYgqdfOIyuZau_QZkHM-tsoKwE_wCAUpqQ0t8SzvIWb1KBLQf_G113S93' >> /opt/amazon-ai/.env
fi

echo ""
echo "=== Current SP-API vars in .env ==="
grep "AMAZON_SP_API" /opt/amazon-ai/.env
