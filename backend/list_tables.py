import os
from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://postgres.hsrhqfyudlmbfedfrasw:SharathPrime10%24@aws-0-ap-south-1.pooler.supabase.com:6543/postgres'
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public';"))
        tables = [row[0] for row in result.fetchall()]
        print("TABLES_START")
        for t in tables:
            print(t)
        print("TABLES_END")
except Exception as e:
    print('ERROR:', e)
