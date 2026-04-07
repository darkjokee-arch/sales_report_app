import sqlite3

conn = sqlite3.connect("sales_db.sqlite")
cursor = conn.cursor()

# 1, 2 = 옥상방수(2026년 예정)
cursor.execute("UPDATE reports SET construction_types = '옥상방수' WHERE notes IN ('PDF 일괄 업로드', 'PDF 일괄 업로드 (추가분)')")
# 3, 4 = 균열보수 및 재도장(2026년 예정)
cursor.execute("UPDATE reports SET construction_types = '균열보수 및 재도장' WHERE notes IN ('PDF 일괄 업로드 (3차)', 'PDF 일괄 업로드 (4차)')")
# 5 = 지하주차장 바닥도색
cursor.execute("UPDATE reports SET construction_types = '지하주차장 바닥도색' WHERE notes = 'PDF 일괄 업로드 (5차)'")
# 6 = 내부도장(2026년 예정)
cursor.execute("UPDATE reports SET construction_types = '내부도장' WHERE notes = 'PDF 일괄 업로드 (6차)'")

conn.commit()
print(f"Updated records.")
conn.close()
