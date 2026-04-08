#!/bin/bash
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys, json
d = json.load(sys.stdin)
for p, v in d['paths'].items():
    if 'agent' in p.lower():
        for m in v.keys():
            print(m.upper(), p)
"
