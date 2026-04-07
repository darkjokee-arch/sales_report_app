import sqlite3
import subprocess
try:
    conn = sqlite3.connect('sales_db.sqlite', timeout=10)
    c = conn.cursor()
    c.execute("UPDATE reports SET kapt_code = 'A10027953' WHERE complex_name LIKE '%하계%' OR complex_name LIKE '%청라%'")
    conn.commit()
    conn.close()
    print('DB K-Code injected successfully.')
except Exception as e:
    print('DB Error:', e)

print('Running kapt_reserve_sync.py manually...')
subprocess.run(['python', 'kapt_reserve_sync.py'], env={'PYTHONUNBUFFERED': '1'})
