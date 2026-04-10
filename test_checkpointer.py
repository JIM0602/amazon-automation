"""Test checkpointer initialization."""
import logging
logging.basicConfig(level=logging.DEBUG)

from langgraph.checkpoint.postgres import PostgresSaver

db_url = "postgresql://app_user:changeme@postgres:5432/amazon_ai"

try:
    ctx = PostgresSaver.from_conn_string(db_url)
    print(f"Type: {type(ctx)}")
    print(f"Has __enter__: {hasattr(ctx, '__enter__')}")
    
    if hasattr(ctx, "__enter__"):
        saver = ctx.__enter__()
        print(f"Saver type: {type(saver)}")
        print(f"Has setup: {hasattr(saver, 'setup')}")
        saver.setup()
        print("Setup succeeded!")
    else:
        print("Not a context manager, trying direct setup")
        ctx.setup()
        print("Direct setup succeeded!")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
