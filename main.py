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
                target_year INTEGER DEFAULT 2026,
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
        # 마이그레이션: target_year 컬럼 idempotent 추가 + 기존 NULL → 2026
        cursor.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS target_year INTEGER DEFAULT 2026")
        cursor.execute("UPDATE reports SET target_year = 2026 WHERE target_year IS NULL")
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
                target_year INTEGER DEFAULT 2026,
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
        # 마이그레이션: SQLite는 IF NOT EXISTS 미지원 → PRAGMA로 컬럼 존재 검사
        cursor.execute("PRAGMA table_info(reports)")
        existing_cols = [r[1] for r in cursor.fetchall()]
        if 'target_year' not in existing_cols:
            cursor.execute("ALTER TABLE reports ADD COLUMN target_year INTEGER DEFAULT 2026")
        cursor.execute("UPDATE reports SET target_year = 2026 WHERE target_year IS NULL")
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
            cursor.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, complex_name TEXT NOT NULL, property_type TEXT, households TEXT, address TEXT NOT NULL, manager_name TEXT, contact TEXT, construction_types TEXT, assigned_company TEXT DEFAULT '미정', recommended_company TEXT DEFAULT '', status TEXT DEFAULT '방문전', notes TEXT, kcc_requests TEXT DEFAULT '', photo_url TEXT, kapt_code TEXT DEFAULT '', long_term_reserve TEXT DEFAULT '', target_year INTEGER DEFAULT 2026, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
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
    target_year: Optional[int] = 2026

class ReportUpdate(BaseModel):
    status: Optional[str] = None
    assigned_company: Optional[str] = None
    notes: Optional[str] = None
    kcc_requests: Optional[str] = None
    complex_name: Optional[str] = None
    address: Optional[str] = None
    kapt_code: Optional[str] = None
    target_year: Optional[int] = None

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
        (complex_name, property_type, households, address, manager_name, contact, construction_types, assigned_company, recommended_company, notes, kcc_requests, photo_url, target_year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''), (
        report.complex_name, report.property_type, report.households, report.address,
        report.manager_name, report.contact, report.construction_types,
        "미정", recommended, report.notes, report.kcc_requests, report.photo_url,
        report.target_year or 2026
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
    if report.target_year is not None:
        updates.append("target_year = " + ("%" + "s" if DB_TYPE == "postgres" else "?"))
        params.append(report.target_year)

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
    target_year: Optional[int] = 2026
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# --- K-APT 장기수선충당금 동기화 (운영 PG 전용) ---
import urllib.parse
import urllib.request
import threading
import difflib

KAPT_API_KEY = "dcc614fd303886a1fcaf68d8ef0eb5720a321b324e84973ee83561c34f000bf3"
KAPT_URL_BASIS = "https://apis.data.go.kr/1613000/AptListService3/getSigunguAptList3"
KAPT_URL_RESERVE = "https://apis.data.go.kr/1613000/AptRepairsCostServiceV2/getHsmpReserveBalanceInfoV2"

KAPT_BJDCE = {
    "종로구":"11110","중구":"11140","용산구":"11170","성동구":"11200","광진구":"11215",
    "동대문구":"11230","중랑구":"11260","성북구":"11290","강북구":"11305","도봉구":"11320",
    "노원구":"11350","은평구":"11380","서대문구":"11410","마포구":"11440","양천구":"11470",
    "강서구":"11500","구로구":"11530","금천구":"11545","영등포구":"11560","동작구":"11590",
    "관악구":"11620","서초구":"11650","강남구":"11680","송파구":"11710","강동구":"11740",
    "인천 중구":"28110","인천 동구":"28140","미추홀구":"28177","연수구":"28185","남동구":"28200",
    "부평구":"28237","계양구":"28245","인천 서구":"28260","강화군":"28710","옹진군":"28720",
    "수원시 장안구":"41111","수원시 권선구":"41113","수원시 팔달구":"41115","수원시 영통구":"41117",
    "장안구":"41111","권선구":"41113","팔달구":"41115","영통구":"41117",
    "성남시 수정구":"41131","성남시 중원구":"41133","성남시 분당구":"41135",
    "수정구":"41131","중원구":"41133","분당구":"41135","의정부시":"41150",
    "안양시 만안구":"41171","안양시 동안구":"41173","만안구":"41171","동안구":"41173",
    "부천시":"41190","광명시":"41210","평택시":"41220","동두천시":"41250",
    "안산시 상록구":"41271","안산시 단원구":"41273","상록구":"41271","단원구":"41273",
    "고양시 덕양구":"41281","고양시 일산동구":"41285","고양시 일산서구":"41287",
    "덕양구":"41281","일산동구":"41285","일산서구":"41287",
    "과천시":"41290","구리시":"41310","남양주시":"41360","오산시":"41370","시흥시":"41390",
    "군포시":"41410","의왕시":"41430","하남시":"41450",
    "용인시 처인구":"41461","용인시 기흥구":"41463","용인시 수지구":"41465",
    "처인구":"41461","기흥구":"41463","수지구":"41465",
    "파주시":"41480","이천시":"41500","안성시":"41550","김포시":"41570",
    "화성시":"41590","광주시":"41610","양주시":"41630","포천시":"41650","여주시":"41670",
    "연천군":"41800","가평군":"41820","양평군":"41830"
}

_sync_state = {"running": False, "total": 0, "done": 0, "updated": 0, "log": []}
_sync_lock = threading.Lock()


def _kapt_http_get(url: str, params: dict, timeout: int = 10) -> dict:
    qs = urllib.parse.urlencode(params, safe=":/+=")
    full = url + "?" + qs
    req = urllib.request.Request(full, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resolve_kapt_code(address: str, complex_name: str) -> str:
    bjdce = "11650"
    for k, v in KAPT_BJDCE.items():
        if k in address:
            bjdce = v
            break
    try:
        data = _kapt_http_get(KAPT_URL_BASIS, {
            "serviceKey": KAPT_API_KEY, "sigunguCode": bjdce,
            "numOfRows": "1000", "pageNo": "1", "_type": "json"
        }, timeout=10)
        body = data.get("response", {}).get("body", {})
        items = body.get("items", [])
        if isinstance(items, dict): items = items.get("item", [])
        if isinstance(items, dict): items = [items]
        if not items: return ""
        clean = complex_name.replace("아파트", "").replace(" ", "")
        best, best_ratio = "", 0.0
        for it in items:
            api_name = it.get("kaptName", "").replace("아파트", "").replace(" ", "")
            if clean in api_name or api_name in clean:
                return it.get("kaptCode", "")
            ratio = difflib.SequenceMatcher(None, clean, api_name).ratio()
            if ratio > best_ratio:
                best_ratio, best = ratio, it.get("kaptCode", "")
        return best if best_ratio > 0.55 else ""
    except Exception as e:
        print(f"[KAPT basis err] {complex_name}: {e}")
        return ""


def _fetch_reserve_balance(kapt_code: str) -> str:
    if not kapt_code: return ""
    network_err = False
    for i in range(1, 7):
        m = datetime.datetime.now().month - i
        y = datetime.datetime.now().year
        if m <= 0:
            m += 12; y -= 1
        date = f"{y:04d}{m:02d}"
        try:
            data = _kapt_http_get(KAPT_URL_RESERVE, {
                "serviceKey": KAPT_API_KEY, "kaptCode": kapt_code,
                "searchDate": date, "_type": "json"
            }, timeout=8)
            body = data.get("response", {}).get("body", {})
            item = body.get("item") or body.get("items", {}).get("item", [])
            if isinstance(item, dict): item = [item]
            if item:
                amt = item[0].get("sTot") or item[0].get("lsbbmAmt")
                if amt and str(amt).strip() not in ("0", "None", ""):
                    return f"{int(str(amt).replace(',', '').strip()):,}원"
        except Exception as e:
            print(f"[KAPT reserve err] {kapt_code} {date}: {e}")
            network_err = True
    return "조회 실패" if network_err else "자료미제출"


def _sync_reserve_worker(year: int, pin: str):
    if pin != ADMIN_PIN:
        with _sync_lock:
            _sync_state["log"].append("ADMIN_PIN 불일치, 종료")
            _sync_state["running"] = False
        return
    try:
        conn = get_raw_connection()
        cursor = conn.cursor()
        cursor.execute(ph(
            "SELECT id, complex_name, address, kapt_code, long_term_reserve "
            "FROM reports WHERE target_year = ? "
            "AND (long_term_reserve IS NULL OR long_term_reserve = '' "
            "OR long_term_reserve = '조회 전' OR long_term_reserve = '조회 실패')"
        ), (year,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        with _sync_lock:
            _sync_state["total"] = len(rows)
            _sync_state["done"] = 0
            _sync_state["updated"] = 0
            _sync_state["log"].append(f"[{year}년] 동기화 대상 {len(rows)}건")

        for row in rows:
            r_id = row["id"]
            name = row["complex_name"]
            addr = row["address"]
            k_code = row.get("kapt_code") or ""

            if not k_code:
                k_code = _resolve_kapt_code(addr, name)
                if k_code:
                    wc = get_raw_connection()
                    wcur = wc.cursor()
                    wcur.execute(ph("UPDATE reports SET kapt_code = ? WHERE id = ?"), (k_code, r_id))
                    wc.commit(); wc.close()

            balance = _fetch_reserve_balance(k_code)
            if balance:
                wc = get_raw_connection()
                wcur = wc.cursor()
                wcur.execute(ph("UPDATE reports SET long_term_reserve = ? WHERE id = ?"), (balance, r_id))
                wc.commit(); wc.close()
                with _sync_lock:
                    _sync_state["updated"] += 1

            with _sync_lock:
                _sync_state["done"] += 1

        with _sync_lock:
            _sync_state["log"].append(f"[{year}년] 완료: {_sync_state['updated']}/{_sync_state['total']} 업데이트")
    except Exception as e:
        with _sync_lock:
            _sync_state["log"].append(f"치명 오류: {e}")
    finally:
        with _sync_lock:
            _sync_state["running"] = False


class SyncReserveRequest(BaseModel):
    pin: str
    target_year: int = 2027


@app.post("/api/admin/sync-reserve")
def sync_reserve_admin(req: SyncReserveRequest):
    if req.pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Invalid admin PIN")
    with _sync_lock:
        if _sync_state["running"]:
            return {"success": False, "message": "이미 동기화 진행 중", "state": dict(_sync_state)}
        _sync_state["running"] = True
        _sync_state["log"] = []
    t = threading.Thread(target=_sync_reserve_worker, args=(req.target_year, req.pin), daemon=True)
    t.start()
    return {"success": True, "message": f"{req.target_year}년 K-APT 동기화 시작", "target_year": req.target_year}


@app.get("/api/admin/sync-reserve/status")
def sync_reserve_status():
    with _sync_lock:
        return dict(_sync_state)


@app.post("/api/bulk-import")
def bulk_import(reports: List[BulkReport], db=Depends(get_db)):
    cursor = db.cursor()
    imported = 0
    for r in reports:
        cursor.execute(ph('''
            INSERT INTO reports
            (complex_name, property_type, households, address, manager_name, contact,
             construction_types, assigned_company, recommended_company, status, notes,
             kcc_requests, photo_url, kapt_code, long_term_reserve, target_year, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''), (
            r.complex_name, r.property_type, r.households, r.address,
            r.manager_name, r.contact, r.construction_types, r.assigned_company,
            r.recommended_company, r.status, r.notes, r.kcc_requests,
            r.photo_url, r.kapt_code, r.long_term_reserve, r.target_year or 2026,
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
