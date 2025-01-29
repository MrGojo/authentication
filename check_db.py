import sqlite3
import os
from pprint import pprint

# Use the same database path as in your app
DATABASE_PATH = 'database/users.db'

def view_database():
    if not os.path.exists(DATABASE_PATH):
        print(f"Database file not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # View tables
    print("\n=== Tables in database ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    for table in tables:
        print(f"\n=== Contents of {table[0]} ===")
        cursor.execute(f"SELECT * FROM {table[0]}")
        columns = [description[0] for description in cursor.description]
        print("Columns:", columns)
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print("\nRow:", dict(zip(columns, row)))
        else:
            print("No data in table")

    conn.close()

if __name__ == "__main__":
    view_database()