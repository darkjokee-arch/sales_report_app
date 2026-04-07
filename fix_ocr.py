import sqlite3

replacements = {
    # 아파트 이름 및 지역 오타
    "평태": "평택",
    "월맘": "힐맘",
    "상환": "삼환",
    "고앙": "고양",
    "한앙": "한양",
    "리버파크]": "리버파크",
    "영동포": "영등포",
    "영중": "영종",
    "하들도시": "하늘도시",
    "유승한내를": "유승한내들",
    "합신더류": "한신더휴",
    "중남": "충남",
    "승림": "송림",
    "풍립": "풍림",
    "승도": "송도",
    "준천": "춘천",
    "코아빌리": "코아빌라",
    "더산": "더샵",
    "푸르지우": "푸르지오",
    "엘센트루": "엘센트로",
    "개술": "캐슬",
    "자연엔": "자연앤",
    "에이저": "메이저",
    "파추": "파주",
    "마율": "마을",
    "웨미리": "훼미리",
    "통원로알류크": "동원로얄듀크",
    "동원로알듀크": "동원로얄듀크",
    "센트컬타운": "센트럴타운",
    "입친주얀": "인천주안",
    "한술시티": "한숲시티",
    "동단": "동탄",
    "천한": "천안",
    "순속아을": "숲속마을",
    "화성등탄": "화성동탄",
    "출선": "춘천",
    "남양추": "남양주",
    "가앙": "가양",
    "헌대": "현대",
    "응인": "용인",
    "버들치마음": "버들치마을",
    "더푼": "덕풍",
    "정담래미안": "청담래미안",
    "한산호수": "안산호수",
    "대립이편한세상": "대림이편한세상",
    "불국마을": "불곡마을",
    "들투팅": "블루밍",
    "성북중암": "성북종암",
    "서대둔": "서대문",
    "컬리사로": "궐리사로",
    "월동": "원동",
    "필동": "원동",
    "벗꽃로": "벚꽃로",
    "세종시용마을": "새뜸마을",
    "더살": "더샵",
    "세중": "세종",
    "/단지": "7단지",
    "종암2차SK$": "종암2차SK뷰"
}

def clean_text(text):
    if not text:
        return text
    new_text = text
    for old, new in replacements.items():
        if old == "종암2차SK$":
            if new_text.endswith("종암2차SK"):
                new_text = new_text.replace("종암2차SK", "종암2차SK뷰")
        else:
            new_text = new_text.replace(old, new)
    return new_text

conn = sqlite3.connect("sales_db.sqlite")
cursor = conn.cursor()

cursor.execute("SELECT id, complex_name, address FROM reports")
rows = cursor.fetchall()
updated_count = 0

for row in rows:
    report_id, name, address = row
    
    new_name = clean_text(name)
    new_address = clean_text(address)
    
    if new_name != name or new_address != address:
        cursor.execute("UPDATE reports SET complex_name = ?, address = ? WHERE id = ?", (new_name, new_address, report_id))
        updated_count += 1
        print(f"[{report_id}] {name} -> {new_name} // {address} -> {new_address}")

conn.commit()
conn.close()

print(f"Total {updated_count} records corrected.")
