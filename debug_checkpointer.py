"""Debug checkpointer connection issue in uvicorn startup."""
import logging
logging.basicConfig(level=logging.DEBUG)

import psycopg

# Direct connection test first
db_url = "postgresql://app_user:changeme@postgres:5432/amazon_ai"
print(f"Testing direct psycopg connection...")
conn = psycopg.connect(db_url)
print(f"Direct connection: {conn.info.status}")
conn.close()

# Now test via langgraph
from langgraph.checkpoint.postgres import PostgresSaver
print(f"\nTesting PostgresSaver.from_conn_string...")
ctx = PostgresSaver.from_conn_string(db_url)
print(f"ctx type: {type(ctx)}")
saver = ctx.__enter__()
print(f"saver type: {type(saver)}")
print(f"saver.conn: {saver.conn}")
print(f"saver.conn closed?: {saver.conn.closed}")
saver.setup()
print("Setup OK!")
