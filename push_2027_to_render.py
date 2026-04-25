"""로컬 SQLite의 2027 데이터를 운영 Render PG로 bulk-import API 통해 push."""
import sqlite3
import json
import urllib.request
import sys

API_URL = "https://sales-report-app-92ed.onrender.com/api/bulk-import"
DB_PATH = "sales_db.sqlite"


def fetch_2027_rows():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reports WHERE target_year = 2027")
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def to_payload(row):
    """BulkReport 모델 형식으로 변환."""
    payload = {
        "complex_name": row.get("complex_name") or "",
        "property_type": row.get("property_type") or "",
        "households": row.get("households") or "",
        "address": row.get("address") or "",
        "manager_name": row.get("manager_name") or "",
        "contact": row.get("contact") or "",
        "construction_types": row.get("construction_types") or "",
        "assigned_company": row.get("assigned_company") or "미정",
        "recommended_company": row.get("recommended_company") or "",
        "status": row.get("status") or "방문전",
        "notes": row.get("notes") or "",
        "kcc_requests": row.get("kcc_requests") or "",
        "photo_url": row.get("photo_url") or "",
        "kapt_code": row.get("kapt_code") or "",
        "long_term_reserve": row.get("long_term_reserve") or "",
        "target_year": 2027,
    }
    return payload


def main():
    rows = fetch_2027_rows()
    print(f"로컬 2027 건수: {len(rows)}")
    if not rows:
        print("푸시할 데이터 없음")
        return

    payload = [to_payload(r) for r in rows]
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"응답: {result}")
    except urllib.error.HTTPError as e:
        print(f"HTTP 에러 {e.code}: {e.read().decode('utf-8', errors='replace')[:500]}")
        sys.exit(1)
    except Exception as e:
        print(f"예외: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
