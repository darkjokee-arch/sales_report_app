import sqlite3
import os

db_path = "sales_db.sqlite"
if not os.path.exists(db_path):
    print("Database not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# "PDF 일괄 업로드"가 포함된 모든 문구를 지웁니다 ("PDF 일괄 업로드 (6차)" 등 포함).
cursor.execute("UPDATE reports SET notes = TRIM(REPLACE(notes, 'PDF 일괄 업로드 (6차)', ''))")
cursor.execute("UPDATE reports SET notes = '' WHERE notes LIKE '%PDF 일괄 업로드%'")

changed = cursor.rowcount
conn.commit()
conn.close()

print(f"Notes containing 'PDF 일괄 업로드' have been deleted or cleared for {changed} records.")
