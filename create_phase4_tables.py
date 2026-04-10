"""Create missing Phase 4 tables."""
from sqlalchemy import create_engine, text
import os

db_url = os.environ.get("DATABASE_URL", "postgresql://app_user:changeme@postgres:5432/amazon_ai")
engine = create_engine(db_url)

with engine.connect() as conn:
    # Check existing tables
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' ORDER BY table_name
    """))
    existing = {row[0] for row in result}
    print(f"Existing tables: {sorted(existing)}")

    # Create conversations if missing
    if "conversations" not in existing:
        conn.execute(text("""
            CREATE TABLE conversations (
                id UUID PRIMARY KEY,
                user_id VARCHAR(256) NOT NULL,
                agent_type VARCHAR(128) NOT NULL,
                title VARCHAR(512),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ,
                metadata_json JSONB
            )
        """))
        print("Created: conversations")

    # Create chat_messages if missing
    if "chat_messages" not in existing:
        conn.execute(text("""
            CREATE TABLE chat_messages (
                id UUID PRIMARY KEY,
                conversation_id UUID NOT NULL REFERENCES conversations(id),
                role VARCHAR(32) NOT NULL,
                content TEXT NOT NULL,
                metadata_json JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX ix_chat_messages_conversation_id ON chat_messages(conversation_id)"))
        print("Created: chat_messages")

    # Create keyword_libraries if missing
    if "keyword_libraries" not in existing:
        conn.execute(text("""
            CREATE TABLE keyword_libraries (
                id UUID PRIMARY KEY,
                product_id UUID REFERENCES products(id),
                keyword VARCHAR(512) NOT NULL,
                search_volume INTEGER,
                relevance_tier VARCHAR(32),
                source VARCHAR(64) NOT NULL,
                category VARCHAR(128),
                monthly_rank INTEGER,
                last_updated TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        conn.execute(text("CREATE INDEX ix_keyword_libraries_keyword ON keyword_libraries(keyword)"))
        print("Created: keyword_libraries")

    # Create ad_simulations if missing
    if "ad_simulations" not in existing:
        conn.execute(text("""
            CREATE TABLE ad_simulations (
                id UUID PRIMARY KEY,
                campaign_id VARCHAR(256),
                simulation_params JSONB,
                results JSONB,
                created_by VARCHAR(256),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        print("Created: ad_simulations")

    # Create ad_optimization_logs if missing
    if "ad_optimization_logs" not in existing:
        conn.execute(text("""
            CREATE TABLE ad_optimization_logs (
                id UUID PRIMARY KEY,
                campaign_id VARCHAR(256),
                action_type VARCHAR(128) NOT NULL,
                old_value JSONB,
                new_value JSONB,
                reason TEXT,
                applied BOOLEAN NOT NULL DEFAULT false,
                approved_by VARCHAR(256),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        print("Created: ad_optimization_logs")

    # Create kb_review_queue if missing
    if "kb_review_queue" not in existing:
        conn.execute(text("""
            CREATE TABLE kb_review_queue (
                id UUID PRIMARY KEY,
                content TEXT NOT NULL,
                source VARCHAR(256),
                agent_type VARCHAR(128),
                summary TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                reviewer_id VARCHAR(256),
                review_comment TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                reviewed_at TIMESTAMPTZ
            )
        """))
        print("Created: kb_review_queue")

    # Create auditor_logs if missing
    if "auditor_logs" not in existing:
        conn.execute(text("""
            CREATE TABLE auditor_logs (
                id UUID PRIMARY KEY,
                agent_type VARCHAR(128) NOT NULL,
                agent_run_id UUID REFERENCES agent_runs(id),
                severity VARCHAR(32) NOT NULL,
                finding TEXT NOT NULL,
                auto_action VARCHAR(32),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        print("Created: auditor_logs")

    # Add missing columns to agent_runs
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'agent_runs'
    """))
    agent_runs_cols = {row[0] for row in result}
    
    if "conversation_id" not in agent_runs_cols:
        conn.execute(text("ALTER TABLE agent_runs ADD COLUMN conversation_id UUID"))
        print("Added column: agent_runs.conversation_id")
    
    if "is_chat_mode" not in agent_runs_cols:
        conn.execute(text("ALTER TABLE agent_runs ADD COLUMN is_chat_mode BOOLEAN DEFAULT false"))
        print("Added column: agent_runs.is_chat_mode")

    # Add missing columns to products
    result = conn.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'products'
    """))
    products_cols = {row[0] for row in result}
    
    if "brand_analytics_keywords" not in products_cols:
        conn.execute(text("ALTER TABLE products ADD COLUMN brand_analytics_keywords JSONB"))
        print("Added column: products.brand_analytics_keywords")

    conn.commit()
    
    # Final check
    result = conn.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' ORDER BY table_name
    """))
    print(f"\nFinal tables: {sorted(row[0] for row in result)}")
    print("\nDone!")
