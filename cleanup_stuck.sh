#!/bin/bash
sudo docker exec amazon-ai-app python3 -c "
from src.db.connection import get_session_local
from src.db.models import AgentRun
from datetime import datetime, timezone
db = get_session_local()()
stuck = db.query(AgentRun).filter(AgentRun.status == 'running').all()
print(f'Stuck running records: {len(stuck)}')
for r in stuck:
    print(f'  {r.id} | {r.agent_type}')

# Clean up: mark stuck runs as failed
for r in stuck:
    r.status = 'failed'
    r.output_summary = 'Stuck in running state - cleaned up'
    r.finished_at = datetime.now(timezone.utc)
db.commit()
print(f'Cleaned up {len(stuck)} stuck records')
db.close()
" 2>&1
