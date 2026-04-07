import sqlite3
import re
import os

db_path = "sales_db.sqlite"
if not os.path.exists(db_path):
    print("DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

file_to_type = {
    "import_ocr.py": "옥상방수",
    "import_ocr_2.py": "옥상방수",
    "import_ocr_3.py": "균열보수 및 재도장",
    "import_ocr_4.py": "균열보수 및 재도장",
    "import_ocr_5.py": "지하주차장 바닥도색",
    "import_ocr_6.py": "내부도장"
}

updated_count = 0

for file_name, ctype in file_to_type.items():
    if not os.path.exists(file_name):
        continue
        
    with open(file_name, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'data\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if match:
        data_str = match.group(1)
        try:
            # safely evaluate the array of tuples
            items = eval('[' + data_str + ']')
            for item in items:
                complex_name = item[0]
                contact = item[2]
                
                # First try by contact
                cursor.execute("""
                    UPDATE reports 
                    SET construction_types = ? 
                    WHERE contact = ? 
                      AND (construction_types IS NULL OR construction_types = '')
                """, (ctype, contact))
                
                # If contact didn't match perfectly, fallback to fuzzy name match
                if cursor.rowcount == 0:
                    cursor.execute("""
                        UPDATE reports 
                        SET construction_types = ? 
                        WHERE complex_name LIKE ? 
                          AND (construction_types IS NULL OR construction_types = '')
                    """, (ctype, f"%{complex_name[:4]}%"))

                # Keep track of records updated
                # Note: exact match rowcount might hit multiple if duplicates exist
                updated_count += cursor.rowcount

        except Exception as e:
            print(f"Error parsing data in {file_name}: {e}")

conn.commit()
conn.close()

print(f"Restored missing construction types for {updated_count} records.")
