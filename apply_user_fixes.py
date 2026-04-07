import sqlite3
import os
from main import determine_company_by_address

db_path = "sales_db.sqlite"
if not os.path.exists(db_path):
    print("Database not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. 상태 일괄 변경: 영업중 -> 방문전
cursor.execute("UPDATE reports SET status = '방문전' WHERE status = '영업중'")
changed_status = cursor.rowcount

# 2. 권역별 추천업체 재할당 및 담당회사 '미정' 처리
cursor.execute("SELECT id, address FROM reports")
rows = cursor.fetchall()

updated_companies = 0
for row in rows:
    report_id, address = row
    recommended = determine_company_by_address(address)
    
    # 미정 처리 및 추천업체 주입
    cursor.execute("UPDATE reports SET recommended_company = ?, assigned_company = '미정' WHERE id = ?", (recommended, report_id))
    updated_companies += 1

conn.commit()
conn.close()

print(f"Status changed '영업중' to '방문전' for {changed_status} rows.")
print(f"Assigned '미정' and pushed recommended companies for {updated_companies} rows.")
print("All requested bulk DB fixes completed successfully.")
