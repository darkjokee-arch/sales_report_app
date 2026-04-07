import sqlite3
import os

db_path = "sales_db.sqlite"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE reports SET status = '방문전'")
    conn.commit()
    conn.close()
    print("All statuses updated to '방문전'.")
else:
    print("Database not found.")
