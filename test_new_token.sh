#!/bin/bash
# Test new Ads refresh token directly via LWA
CLIENT_ID="amzn1.application-oa2-client.0ae5b1bd03014705bd85566ddde90054"
CLIENT_SECRET="amzn1.oa2-cs.v1.3074cc3c5b2abda26699f670802f8e5d178555399802e018a94c764fbad54597"
REFRESH_TOKEN='Atzr|IwEBIBLQI941sd1QokrTFK4K48dpWqX1xh6JIbS9DR-i3Fmo3AXLbS4QT9Q-h_GSudQvSLH2j5FwDIgdyA7ikc7UpOM-aVWFE_X2hpFA3vz7kgEQewyRcuUf5yO1l3sWMhQehjN_8yQQBI1c-c-tJZVdqXcwquFc25k9264jMyzY5WjIBxoCXCOiKnrQDYBTSQK8d_wmoVJopzhVsG-anLkM4SKIBmxLp7vby5fEQpmcWqHDyTyScb-2JwnyBH5vEPSRkCFoudEfU0oIacsW9e1XFqNbW3JjaeK9XsVVn9RafNl0oTaw0z78Bx31D3v1LYNEztB4uxt_dFjaOZCsbNgD5H0hdcWLc4wRRrp9Hko9aLq25D1WCh01T2sJ-Qgja8Lf3T1ABbUJJ44jbEt6PGMPHjS6U5FSfiishSzHjLVsBDqKGpeeak_T9tnEOhX9Ry5QvD7m8TlbnjFFIZNrpBrL8CsqYDP603yYkBPaYSNJQxHSjT-ATy2dRcsxs-DNlFHW3vrlOq5w5uWg8z_pLBYME_Eq'

echo "=== Testing new Ads refresh token ==="
echo "Token length: ${#REFRESH_TOKEN}"
RESP=$(curl -s -X POST https://api.amazon.com/auth/o2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=refresh_token" \
  --data-urlencode "refresh_token=$REFRESH_TOKEN" \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "client_secret=$CLIENT_SECRET")
echo "Response: $RESP"
echo ""

# Check if we got an access_token
echo "$RESP" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if 'access_token' in d:
        print('SUCCESS! Got access_token, expires_in=' + str(d.get('expires_in','')))
    else:
        print('FAILED: ' + json.dumps(d, indent=2))
except:
    print('FAILED: could not parse response')
"
