import sqlite3

conn = sqlite3.connect("sales_db.sqlite")
c = conn.cursor()
c.execute("INSERT INTO reports (complex_name, address, status, notes) VALUES ('고양 가좌마을1단지아파트', '경기 고양시 일산서구 가좌동 123', '타사검토요청(토스)', '')")
conn.commit()
conn.close()
print("Test record inserted")
