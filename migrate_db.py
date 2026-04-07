import sqlite3

conn = sqlite3.connect("sales_db.sqlite")
cursor = conn.cursor()

# 1. Add column if not exists
try:
    cursor.execute("ALTER TABLE reports ADD COLUMN kcc_requests TEXT DEFAULT ''")
    print("Added kcc_requests column.")
except sqlite3.OperationalError:
    print("kcc_requests column already exists.")

# 2. Update company names in DB
company_mapping = {
    "회사1": "세일산업개발",
    "회사2": "세진씨엔씨",
    "회사3": "더세움",
    "회사4": "유니드건설"
}
for old_name, new_name in company_mapping.items():
    cursor.execute("UPDATE reports SET assigned_company = ? WHERE assigned_company = ?", (new_name, old_name))

# 3. Update status names in DB
status_mapping = {
    "수주완료": "계약완료",
    "타사낙찰": "타사공사완료",
    "타사검토요청": "타사검토요청(토스)"
}
for old_status, new_status in status_mapping.items():
    cursor.execute("UPDATE reports SET status = ? WHERE status = ?", (new_status, old_status))

conn.commit()
print("Database schema and data migrated.")
conn.close()
