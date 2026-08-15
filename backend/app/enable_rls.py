import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(".")))
from sqlalchemy import text

from app.db.database import SessionLocal

db = SessionLocal()
try:
    # Get all tables in public schema
    result = db.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
    )
    tables = [row[0] for row in result.fetchall()]

    for table in tables:
        print(f"Enabling RLS on {table}...")
        db.execute(text(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY;'))

    db.commit()
    print("Successfully enabled RLS on all tables.")
except Exception as e:
    print("ERROR:", e)
