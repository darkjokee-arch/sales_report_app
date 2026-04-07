import sqlite3

conn = sqlite3.connect("sales_db.sqlite")
cursor = conn.cursor()

corrections = [
    ("UPDATE reports SET address = REPLACE(address, '망원동', '망월동') WHERE address LIKE '%망원동%'", []),
    ("UPDATE reports SET address = REPLACE(address, '이왕시', '의왕시') WHERE address LIKE '%이왕시%'", []),
    ("UPDATE reports SET complex_name = REPLACE(complex_name, '이천안솔파크', '이천한솔파크') WHERE complex_name LIKE '%이천안솔파크%'", []),
    ("UPDATE reports SET complex_name = REPLACE(complex_name, '아트원', '아트윈') WHERE complex_name LIKE '%송도아트원%'", []),
    ("UPDATE reports SET complex_name = '오산세교이편한세상' WHERE complex_name = '오산셰교이편한세상'", []),
    ("UPDATE reports SET address = REPLACE(address, '허준로 55-20 (가양동', '허준로 55-20 (가양동)') WHERE address LIKE '%가양동%' AND address NOT LIKE '%)'", []),
    ("UPDATE reports SET complex_name = '청주분평현대대우' WHERE complex_name = '청주분형현대대우'", []),
    ("UPDATE reports SET complex_name = '수원호매실경남아너스빌' WHERE complex_name = '수원호매설경남아너스빌'", []),
    ("UPDATE reports SET complex_name = '대림이편한세상' WHERE complex_name = '대립이편한세상'", []),
    ("UPDATE reports SET complex_name = '은평이편한세상백련산' WHERE complex_name = '은평이편한세앙백련산'", [])
]

for query, params in corrections:
    cursor.execute(query, params)

conn.commit()
print("Specific targeted corrections finished.")
conn.close()
