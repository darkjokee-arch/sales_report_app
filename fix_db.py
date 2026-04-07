import sqlite3
import os

db_path = "sales_db.sqlite"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    mapping = {
        "회사1": "세일산업개발",
        "회사2": "세진씨엔씨",
        "회사3": "더세움",
        "회사4": "유니드건설"
    }
    for old, new in mapping.items():
        cursor.execute("UPDATE reports SET assigned_company = ? WHERE assigned_company = ?", (new, old))
    conn.commit()
    conn.close()
    print("DB company names updated.")
else:
    print("Database not found.")
