import sys
import os
import sqlite3
try:
    import pandas as pd
except ImportError:
    print("pandas not installed")
    sys.exit(1)

file_path = "2026년예정_도장및방수공사수요_260310.xlsx"

# Determine company by address (copied from main.py logic)
def determine_company_by_address(address: str) -> str:
    addr = address.replace(" ", "")
    seil_keywords = ["서대문구", "마포구", "은평구", "종로구", "중구", "동작구", "용산구"]
    sejin_keywords = ["서초구", "강남구", "관악구", "금천구", "구로구", "영등포구", "양천구", "강서구"]
    theseum_keywords = ["일산", "고양시", "파주시", "김포시", "성북구", "강북구", "도봉구", "노원구"]
    unid_keywords = ["하남시", "구리시", "남양주", "송파구", "강동구", "광진구", "성동구", "동대문구", "중랑구"]

    for kw in seil_keywords:
        if kw in addr: return "세일산업개발"
    for kw in sejin_keywords:
        if kw in addr: return "세진씨엔씨"
    for kw in theseum_keywords:
        if kw in addr: return "더세움"
    for kw in unid_keywords:
        if kw in addr: return "유니드건설"
    return "미정"

if not os.path.exists(file_path):
    print("File not found")
    sys.exit(1)

# Read raw excel
try:
    df_raw = pd.read_excel(file_path)
except Exception as e:
    print(f"Failed to read excel: {e}")
    sys.exit(1)

# Extract core construction type from the top-left cell title
title = str(df_raw.columns[0]).replace(" ", "")
const_type = ""
if "내부도장" in title: const_type = "내부도장"
elif "외부도장" in title: const_type = "외부도장"
elif "옥상방수" in title: const_type = "옥상방수"
elif "균열" in title or "재도장" in title: const_type = "균열보수 및 재도장"
elif "지하주차장" in title or "도색" in title: const_type = "지하주차장 바닥도색"
else: const_type = df_raw.columns[0] # Fallback to literal title

# The actual headers are in row 0, data starts from row 1
df = df_raw.copy()
df.columns = df.iloc[0].tolist() 
df = df[1:].reset_index(drop=True)

# Expecting columns: W-ERP 단지명, 세대수, 연락처, 주소, 소장명
db_path = "sales_db.sqlite"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

inserted = 0
updated = 0

for index, row in df.iterrows():
    c_name = str(row.iloc[0]).strip()
    if c_name.lower() == 'nan' or not c_name:
        continue
    households = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
    contact = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
    # Ensure contact is a string not float like 516210651.0
    if contact.endswith('.0'): contact = contact[:-2]
    # zero-pad local numbers like 516210651 -> 0516210651
    if len(contact) == 9 and not contact.startswith('0'):
        contact = '0' + contact
        
    address = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
    manager = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ""
    
    recommended_comp = determine_company_by_address(address)

    # Check if exists by contact (strongest match) or complex name
    cursor.execute("SELECT id FROM reports WHERE contact = ? AND contact != ''", (contact,))
    match = cursor.fetchone()
    
    if not match:
        cursor.execute("SELECT id FROM reports WHERE complex_name LIKE ? AND address LIKE ?", (f"%{c_name[:5]}%", f"%{address[:5]}%"))
        match = cursor.fetchone()

    if match:
        # UPDATE
        report_id = match[0]
        cursor.execute("""
            UPDATE reports SET 
                complex_name = ?,
                households = ?,
                contact = ?,
                address = ?,
                manager_name = ?,
                construction_types = ?
            WHERE id = ?
        """, (c_name, households, contact, address, manager, const_type, report_id))
        updated += 1
    else:
        # INSERT
        cursor.execute("""
            INSERT INTO reports 
            (complex_name, property_type, households, address, manager_name, contact, construction_types, assigned_company, recommended_company, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (c_name, "아파트/오피스텔", households, address, manager, contact, const_type, "미정", recommended_comp, "방문전", ""))
        inserted += 1

conn.commit()
conn.close()

print(f"Successfully processed Excel data!")
print(f"Records updated: {updated}")
print(f"Records newly inserted: {inserted}")
