import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.app.db.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='messages' and column_name='sources';"
            ))
            if not result.fetchone():
                print("Adding 'sources' column to 'messages' table...")
                conn.execute(text("ALTER TABLE messages ADD COLUMN sources JSON DEFAULT '[]'::json;"))
                conn.commit()
                print("Migration successful.")
            else:
                print("Column 'sources' already exists.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
