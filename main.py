from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import datetime
import uvicorn
import re
import os
import json
from fastapi import WebSocket, WebSocketDisconnect

# ---------------------------------------------------------
# DATABASE BACKEND DETECTION
# ---------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    import psycopg2
    import psycopg2.extras
    DB_TYPE = "postgres"
    print(f"✅ [DB] PostgreSQL 모드 (외부 DB 연결)")
else:
    import sqlite3
    DB_TYPE = "sqlite"
    print(f"✅ [DB] SQLite 모드 (로컬 파일)")

# ---------------------------------------------------------
# CONSTANTS & CONFIGURATION
# ---------------------------------------------------------
DB_FILE = "sales_db.sqlite"
APP_PIN = "7890"
ADMIN_PIN = "0000"

companies = {
    "회사1": {"name": "세일산업개발", "region": "마포구 서교동", "color": "bg-blue-500"},
    "회사2": {"name": "세진씨엔씨", "region": "서초구 양재동", "color": "bg-red-500"},
    "회사3": {"name": "더세움", "region": "일산서구 가좌동", "color": "bg-green-500"},
    "회사4": {"name": "유니드건설", "region": "하남시 망월동", "color": "bg-purple-500"}
}

REGIONS_MAPPING = {
    "마포구": "세일산업개발", "서대문구": "세일산업개발", "은평구": "세일산업개발", "강서구": "세일산업개발", "양천구": "세일산업개발", "구로구": "세일산업개발",
    "파주시": "세일산업개발", "김포시": "세일산업개발", "부천시": "세일산업개발", "인천광역시": "세일산업개발", "인천": "세일산업개발",
    "서초구": "세진씨엔씨", "강남구": "세진씨엔씨", "동작구": "세진씨엔씨", "관악구": "세진씨엔씨", "금천구": "세진씨엔씨",
    "과천시": "세진씨엔씨", "성남시": "세진씨엔씨", "분당구": "세진씨엔씨", "안양시": "세진씨엔씨", "수원시": "세진씨엔씨", "용인시": "세진씨엔씨",
    "고양시": "더세움", "일산서구": "더세움", "일산동구": "더세움", "덕양구": "더세움",
    "의정부시": "더세움", "양주시": "더세움", "도봉구": "더세움", "강북구": "더세움",
    "하남시": "유니드건설", "송파구": "유니드건설", "강동구": "유니드건설", "광진구": "유니드건설", "성동구": "유니드건설", "동대문구": "유니드건설",
    "중랑구": "유니드건설", "노원구": "유니드건설", "구리시": "유니드건설", "남양주시": "유니드건설", "종로구": "유니드건설", "중구": "유니드건설", "용산구": "유니드건설"
}

def determine_company_by_address(address: str) -> str:
    for region_keyword, company_id in REGIONS_MAPPING.items():
        if region_keyword in address:
            return company_id
    return "미정"


# ---------------------------------------------------------
# DATABASE HELPERS
# ---------------------------------------------------------
def ph(sql):
    """SQLite ? 플레이스홀더를 PostgreSQL %s로 변환"""
    if DB_TYPE == "postgres":
        return sql.replace("?", "%s")
    return sql

def get_raw_connection():
    """WebSocket 등에서 직접 사용할 DB 연결"""
    if DB_TYPE == "postgres":
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect(DB_FILE)
        return conn


# ---------------------------------------------------------
# DATABASE SETUP
# ---------------------------------------------------------
def init_db():
    if DB_TYPE == "postgres":
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                complex_name TEXT NOT NULL,
                property_type TEXT,
                households TEXT,
                address TEXT NOT NULL,
                manager_name TEXT,
                contact TEXT,
                construction_types TEXT,
                assigned_company TEXT DEFAULT '미정',
                recommended_company TEXT DEFAULT '',
                status TEXT DEFAULT '방문전',
                notes TEXT,
                kcc_requests TEXT DEFAULT '',
                photo_url TEXT,
                kapt_code TEXT DEFAULT '',
                long_term_reserve TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                sender_name TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    else:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complex_name TEXT NOT NULL,
                property_type TEXT,
                households TEXT,
                address TEXT NOT NULL,
                manager_name TEXT,
                contact TEXT,
                construction_types TEXT,
                assigned_company TEXT DEFAULT '미정',
                recommended_company TEXT DEFAULT '',
                status TEXT DEFAULT '방문전',
                notes TEXT,
                kcc_requests TEXT DEFAULT '',
                photo_url TEXT,
                kapt_code TEXT DEFAULT '',
                long_term_reserve TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_name TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

init_db()

def get_db():
    if DB_TYPE == "postgres":
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE created_at <= NOW() - INTERVAL '7 days'")
            conn.commit()
            yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS chat_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_name TEXT NOT NULL, message TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            cursor.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, complex_name TEXT NOT NULL, property_type TEXT, households TEXT, address TEXT NOT NULL, manager_name TEXT, contact TEXT, construction_types TEXT, assigned_company TEXT DEFAULT '미정', recommended_company TEXT DEFAULT '', status TEXT DEFAULT '방문전', notes TEXT, kcc_requests TEXT DEFAULT '', photo_url TEXT, kapt_code TEXT DEFAULT '', long_term_reserve TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            conn.commit()
            cursor.execute("DELETE FROM chat_messages WHERE created_at <= datetime('now', '-7 days')")
            conn.commit()
            yield conn
        finally:
            conn.close()

# ---------------------------------------------------------
# FASTAPI APP & GOLF INTEGRATION (v4.0)
# ---------------------------------------------------------
import sys
from fastapi.middleware.wsgi import WSGIMiddleware

GOLF_PATH = r"C:\Users\hspt8\.gemini\antigravity\scratch\golf_notifier"
if GOLF_PATH not in sys.path:
    sys.path.append(GOLF_PATH)

app = FastAPI(title="공동 영업보고서 & 골프 통합 포털")

try:
    from app import app as golf_flask_app
    app.mount("/golf", WSGIMiddleware(golf_flask_app))
    print("✅ [통합] 골프 관제 센터가 /golf 경로에 성공적으로 부착되었습니다.")
except Exception as e:
    print(f"⚠️ [오류] 골프 앱 통합 실패: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# WebSocket Chat Manager
# ---------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

# API Models
class LoginRequest(BaseModel):
    pin: str

class ReportCreate(BaseModel):
    complex_name: str
    property_type: Optional[str] = ""
    households: Optional[str] = ""
    address: str
    manager_name: Optional[str] = ""
    contact: Optional[str] = ""
    construction_types: Optional[str] = ""
    notes: Optional[str] = ""
    kcc_requests: Optional[str] = ""
    photo_url: Optional[str] = ""

class ReportUpdate(BaseModel):
    status: Optional[str] = None
    assigned_company: Optional[str] = None
    notes: Optional[str] = None
    kcc_requests: Optional[str] = None
    complex_name: Optional[str] = None
    address: Optional[str] = None
    kapt_code: Optional[str] = None

# --- Routes ---
@app.post("/api/verify-pin")
def verify_pin(req: LoginRequest):
    if req.pin == ADMIN_PIN:
        return {"success": True, "message": "Host Authenticated", "is_host": True}
    elif req.pin == APP_PIN:
        return {"success": True, "message": "Authenticated", "is_host": False}
    else:
        raise HTTPException(status_code=401, detail="Invalid PIN")

@app.get("/api/reports")
def get_reports(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM reports ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    return {"reports": [dict(row) for row in rows]}

@app.post("/api/reports")
def create_report(report: ReportCreate, db=Depends(get_db)):
    recommended = determine_company_by_address(report.address)

    cursor = db.cursor()
    cursor.execute(ph('''
        INSERT INTO reports
        (complex_name, property_type, households, address, manager_name, contact, construction_types, assigned_company, recommended_company, notes, kcc_requests, photo_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''), (
        report.complex_name, report.property_type, report.households, report.address,
        report.manager_name, report.contact, report.construction_types,
        "미정", recommended, report.notes, report.kcc_requests, report.photo_url
    ))
    db.commit()

    if DB_TYPE == "postgres":
        cursor.execute("SELECT lastval()")
        new_id = cursor.fetchone()["lastval"]
    else:
        new_id = cursor.lastrowid

    return {"success": True, "id": new_id, "recommended_company": recommended}

@app.put("/api/reports/{report_id}")
async def update_report(report_id: int, report: ReportUpdate, db=Depends(get_db)):
    cursor = db.cursor()

    cursor.execute(ph("SELECT complex_name, status FROM reports WHERE id = ?"), (report_id,))
    row = cursor.fetchone()
    if not row:
        return {"success": False, "message": "Report not found"}

    old_status = dict(row).get("status", "")
    complex_name = dict(row).get("complex_name", "")

    updates = []
    params = []

    if report.status is not None:
        updates.append("status = " + ("%" + "s" if DB_TYPE == "postgres" else "?"))
        params.append(report.status)
    if report.assigned_company is not None:
        updates.append("assigned_company = " + ("%" + "s" if DB_TYPE == "postgres" else "?"))
        params.append(report.assigned_company)
    if report.notes is not None:
        updates.append("notes = " + ("%" + "s" if DB_TYPE == "postgres" else "?"))
        params.append(report.notes)
    if report.kcc_requests is not None:
        updates.append("kcc_requests = " + ("%" + "s" if DB_TYPE == "postgres" else "?"))
        params.append(report.kcc_requests)
    if report.complex_name is not None:
        updates.append("complex_name = " + ("%" + "s" if DB_TYPE == "postgres" else "?"))
        params.append(report.complex_name)
    if report.address is not None:
        updates.append("address = " + ("%" + "s" if DB_TYPE == "postgres" else "?"))
        params.append(report.address)
    if report.kapt_code is not None:
        updates.append("kapt_code = " + ("%" + "s" if DB_TYPE == "postgres" else "?"))
        params.append(report.kapt_code)

    if not updates:
        return {"success": True, "message": "No changes requested"}

    placeholder = "%s" if DB_TYPE == "postgres" else "?"
    updates.append("updated_at = " + placeholder)
    params.append(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    params.append(report_id)

    query = f"UPDATE reports SET {', '.join(updates)} WHERE id = {placeholder}"
    cursor.execute(query, tuple(params))
    db.commit()

    if report.status == "타사검토요청(토스)" and old_status != "타사검토요청(토스)":
        msg_text = f"🔄 [시스템 알림] '{complex_name}' 현장이 타사검토(토스) 건으로 전환되었습니다."
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(ph("INSERT INTO chat_messages (sender_name, message, created_at) VALUES (?, ?, ?)"),
                       ("시스템", msg_text, now_str))
        db.commit()

        payload = json.dumps({
            "sender_name": "시스템",
            "message": msg_text,
            "created_at": now_str
        })
        await manager.broadcast(payload)

    return {"success": True}

@app.delete("/api/reports/{report_id}")
def delete_report(report_id: int, db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute(ph("SELECT id FROM reports WHERE id = ?"), (report_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Report not found")
    cursor.execute(ph("DELETE FROM reports WHERE id = ?"), (report_id,))
    db.commit()
    return {"success": True}

@app.get("/api/companies")
def get_company_info():
    return companies

# --- Chat Routes ---
@app.get("/api/chat/history")
def get_chat_history(db=Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("SELECT sender_name, message, created_at FROM chat_messages ORDER BY id ASC")
    rows = cursor.fetchall()
    return {"messages": [dict(row) for row in rows]}

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            sender_name = data.get("sender_name", "익명")
            message_text = data.get("message", "")

            if not message_text.strip():
                continue

            conn = get_raw_connection()
            cursor = conn.cursor()
            cursor.execute(ph("INSERT INTO chat_messages (sender_name, message) VALUES (?, ?)"), (sender_name, message_text))
            conn.commit()

            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.close()

            broadcast_data = {
                "sender_name": sender_name,
                "message": message_text,
                "created_at": now_str
            }
            await manager.broadcast(json.dumps(broadcast_data))

    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- Bulk Import (데이터 이전용) ---
class BulkReport(BaseModel):
    complex_name: str
    property_type: Optional[str] = ""
    households: Optional[str] = ""
    address: str
    manager_name: Optional[str] = ""
    contact: Optional[str] = ""
    construction_types: Optional[str] = ""
    assigned_company: Optional[str] = "미정"
    recommended_company: Optional[str] = ""
    status: Optional[str] = "방문전"
    notes: Optional[str] = ""
    kcc_requests: Optional[str] = ""
    photo_url: Optional[str] = ""
    kapt_code: Optional[str] = ""
    long_term_reserve: Optional[str] = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@app.post("/api/bulk-import")
def bulk_import(reports: List[BulkReport], db=Depends(get_db)):
    cursor = db.cursor()
    imported = 0
    for r in reports:
        cursor.execute(ph('''
            INSERT INTO reports
            (complex_name, property_type, households, address, manager_name, contact,
             construction_types, assigned_company, recommended_company, status, notes,
             kcc_requests, photo_url, kapt_code, long_term_reserve, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''), (
            r.complex_name, r.property_type, r.households, r.address,
            r.manager_name, r.contact, r.construction_types, r.assigned_company,
            r.recommended_company, r.status, r.notes, r.kcc_requests,
            r.photo_url, r.kapt_code, r.long_term_reserve,
            r.created_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            r.updated_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        imported += 1
    db.commit()
    return {"success": True, "imported": imported}

if __name__ == "__main__":
    init_db()
    if DB_TYPE == "sqlite":
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM reports")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''INSERT INTO reports (complex_name, address, assigned_company, status, notes)
                              VALUES ('샘플 아파트', '서울 마포구 공덕동 123', '세일산업개발', '영업중', '초기 생성 샘플 데이터입니다.')''')
            conn.commit()
        conn.close()

    print("Starting Sales Report API Server on port 8000...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
