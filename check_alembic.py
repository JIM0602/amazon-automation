"""Check Alembic version and stamp to head if needed."""
from sqlalchemy import create_engine, text
import os

db_url = os.environ.get("DATABASE_URL", "postgresql://app_user:changeme@postgres:5432/amazon_ai")
engine = create_engine(db_url)

with engine.connect() as conn:
    # Check current alembic version
    try:
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        versions = [row[0] for row in result]
        print(f"Current alembic versions: {versions}")
    except Exception as e:
        print(f"No alembic_version table: {e}")
    
    # Check if phase4 tables exist
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """))
    tables = [row[0] for row in result]
    print(f"Tables: {tables}")
