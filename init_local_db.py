#!/usr/bin/env python3
"""
init_local_db.py - Local development database initialization script

Creates SQLite database and inserts initial user data.
Usage: python init_local_db.py
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from passlib.hash import bcrypt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, User
from src.config import settings


def main():
    print("=" * 60)
    print("  PUDIWIND Local Database Initialization")
    print("=" * 60)
    
    db_url = settings.DATABASE_URL
    print(f"Database: {db_url}")
    
    # Create engine
    if db_url.startswith("sqlite"):
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(db_url)
    
    # Create all tables
    print("\n[1/3] Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("      [OK] Tables created successfully")
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Check if users already exist
    existing_users = session.query(User).count()
    if existing_users > 0:
        print(f"\n[2/3] Database already has {existing_users} users, skipping user creation")
    else:
        print("\n[2/3] Creating initial users...")
        
        users_data = [
            {"username": "boss", "password": "test123", "role": "boss", "display_name": "Boss"},
            {"username": "op1", "password": "test123", "role": "operator", "display_name": "Operator 1"},
            {"username": "op2", "password": "test123", "role": "operator", "display_name": "Operator 2"},
        ]
        
        for user_data in users_data:
            user = User(
                username=user_data["username"],
                password_hash=bcrypt.hash(user_data["password"]),
                role=user_data["role"],
                display_name=user_data["display_name"],
                is_active=True,
            )
            session.add(user)
            print(f"      [OK] Created user: {user_data['username']} (role: {user_data['role']})")
        
        session.commit()
        print("      [OK] User data committed")
    
    # Verify
    print("\n[3/3] Verifying database...")
    user_count = session.query(User).count()
    print(f"      [OK] Total users: {user_count}")
    
    # List all users
    users = session.query(User).all()
    print("\n" + "-" * 40)
    print("  Available login accounts:")
    print("-" * 40)
    for u in users:
        print(f"  Username: {u.username:<10} Password: test123  Role: {u.role}")
    print("-" * 40)
    
    session.close()
    
    print("\n[OK] Local database initialization complete!")
    print("\nNext steps:")
    print("  1. Start backend: uvicorn src.api.main:app --reload --port 8000")
    print("  2. Start frontend: cd src/frontend && npm run dev")
    print("  3. Visit http://localhost:5173 and login with boss/test123")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
