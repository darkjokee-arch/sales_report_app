import sqlite3

conn = sqlite3.connect("sales_db.sqlite")
cursor = conn.cursor()

# "PDF 일괄 업로드"를 포함하는 메모 내용 지우기
cursor.execute("UPDATE reports SET notes = '' WHERE notes LIKE '%PDF 일괄 업로드%'")
conn.commit()
print(f"Cleared {cursor.rowcount} notes.")

conn.close()
