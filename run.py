import uvicorn
import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from main import app, init_db
import sqlite3

os.makedirs("static", exist_ok=True)

init_db()

# 서버 시작 시 DB 상태 확인
try:
    conn = sqlite3.connect("sales_db.sqlite")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"DB 테이블 목록: {tables}")
    cursor.execute("SELECT COUNT(*) FROM reports")
    count = cursor.fetchone()[0]
    print(f"reports 레코드 수: {count}")
    conn.close()
except Exception as e:
    print(f"DB 확인 에러: {e}")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('templates/index.html')

if __name__ == "__main__":
    init_db()
    # 씨드 데이터 여부 확인
    conn = sqlite3.connect("sales_db.sqlite")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM reports")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''INSERT INTO reports (complex_name, property_type, households, address, manager_name, contact, construction_types, assigned_company, recommended_company, status, notes) 
                          VALUES ('스카이 레지던스', '오피스텔', '300', '서울 마포구 서교동 400', '김철수', '010-9876-5432', '내부도장', '미정', '세일산업개발', '입찰예정', '4월 초 입찰 공고 예정, 시방서 검토 중.')''')
        cursor.execute('''INSERT INTO reports (complex_name, property_type, households, address, manager_name, contact, construction_types, assigned_company, recommended_company, status, notes) 
                          VALUES ('강남타워', '상가', '50', '서울 강남구 역삼동', '박소장', '010-1111-2222', '외부도장', '미정', '세진씨엔씨', '계약완료', '계약서 도장 완료. 착공 준비 중')''')
        cursor.execute('''INSERT INTO reports (complex_name, property_type, households, address, manager_name, contact, construction_types, assigned_company, recommended_company, status, notes) 
                          VALUES ('미사 호수뷰 아파트', '아파트', '800', '경기 하남시 망월동', '이관리', '010-3333-4444', '옥상방수', '미정', '유니드건설', '보류', '올해 공사 예산 없음')''')
        conn.commit()
    conn.close()
    
    print("Starting APP on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
