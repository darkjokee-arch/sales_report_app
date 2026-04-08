import uvicorn
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from main import app, init_db, DB_TYPE, DB_FILE

os.makedirs("static", exist_ok=True)

init_db()

# 서버 시작 시 DB 상태 확인
try:
    if DB_TYPE == "postgres":
        import psycopg2
        from main import DATABASE_URL
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM reports")
        count = cursor.fetchone()[0]
        print(f"[PostgreSQL] reports 레코드 수: {count}")
        conn.close()
    else:
        import sqlite3
        conn = sqlite3.connect(DB_FILE)
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
    print("Starting APP on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
