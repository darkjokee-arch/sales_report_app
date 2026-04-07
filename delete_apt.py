import sqlite3
import os

db_path = "sales_db.sqlite"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reports WHERE complex_name = '늘푸른 아파트'")
    conn.commit()
    conn.close()
    print("Deleted '늘푸른 아파트'.")
