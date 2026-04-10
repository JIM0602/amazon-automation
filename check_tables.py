"""Check Phase 4 required tables and add missing ones."""
from sqlalchemy import create_engine, text
import os

db_url = os.environ.get("DATABASE_URL", "postgresql://app_user:changeme@postgres:5432/amazon_ai")
engine = create_engine(db_url)

PHASE4_TABLES = [
    "conversations", "messages", "approval_requests", 
    "audit_logs", "knowledge_entries", "document_chunks",
    "agent_cost_logs"
]

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """))
    existing = {row[0] for row in result}
    
    print(f"Existing tables: {sorted(existing)}")
    
    missing = [t for t in PHASE4_TABLES if t not in existing]
    if missing:
        print(f"MISSING tables: {missing}")
    else:
        print("All Phase 4 tables exist!")
    
    # Check conversations table columns if it exists
    if "conversations" in existing:
        result = conn.execute(text("""
            SELECT column_name, data_type FROM information_schema.columns 
            WHERE table_name = 'conversations' ORDER BY ordinal_position
        """))
        print(f"\nconversations columns: {[(r[0], r[1]) for r in result]}")
    
    if "messages" in existing:
        result = conn.execute(text("""
            SELECT column_name, data_type FROM information_schema.columns 
            WHERE table_name = 'messages' ORDER BY ordinal_position
        """))
        print(f"\nmessages columns: {[(r[0], r[1]) for r in result]}")
