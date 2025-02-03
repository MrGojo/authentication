import sqlite3
import os
from pprint import pprint

# Use the same database path as in your app
DATABASE_PATH = 'database/users.db'

def check_database_structure():
    if not os.path.exists(DATABASE_PATH):
        print(f"Database file not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("\nDatabase Tables:")
    for table in tables:
        table_name = table[0]
        print(f"\n=== Table: {table_name} ===")
        
        # Get table info
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        print("Columns:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")

    conn.close()

if __name__ == "__main__":
    check_database_structure()