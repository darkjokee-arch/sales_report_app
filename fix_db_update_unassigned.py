import sqlite3
import os

db_path = "sales_db.sqlite"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Update existing reports to have '미정' as assigned_company 
    # and their current assigned_company as recommended_company
    cursor.execute("UPDATE reports SET recommended_company = assigned_company WHERE assigned_company != '미정' AND recommended_company = ''")
    cursor.execute("UPDATE reports SET assigned_company = '미정' WHERE assigned_company != '미정'")
    
    conn.commit()
    conn.close()
    print("DB updated existing reports to unassigned with recommendations.")
else:
    print("Database not found.")
