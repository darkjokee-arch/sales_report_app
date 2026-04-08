"""
SQLite → PostgreSQL 데이터 이전 스크립트

사용법:
  set DATABASE_URL=postgresql://user:pass@host/dbname
  python migrate_to_pg.py
"""
import sqlite3
import os
import sys

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL 환경변수가 설정되지 않았습니다.")
    print("   set DATABASE_URL=postgresql://user:pass@host/dbname")
    sys.exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

import psycopg2

DB_FILE = "sales_db.sqlite"

# SQLite에서 데이터 읽기
sqlite_conn = sqlite3.connect(DB_FILE)
sqlite_conn.row_factory = sqlite3.Row
cursor = sqlite_conn.cursor()
cursor.execute("SELECT * FROM reports")
rows = cursor.fetchall()
reports = [dict(row) for row in rows]
sqlite_conn.close()

print(f"📦 SQLite에서 {len(reports)}건 읽기 완료")

# PostgreSQL에 연결
pg_conn = psycopg2.connect(DATABASE_URL)
pg_cursor = pg_conn.cursor()

# 테이블 생성
pg_cursor.execute('''
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
pg_cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_messages (
        id SERIAL PRIMARY KEY,
        sender_name TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')
pg_conn.commit()

# 기존 데이터 확인
pg_cursor.execute("SELECT COUNT(*) FROM reports")
existing = pg_cursor.fetchone()[0]
if existing > 0:
    print(f"⚠️  PostgreSQL에 이미 {existing}건이 있습니다. 중복 방지를 위해 기존 데이터를 비우고 다시 넣습니다.")
    pg_cursor.execute("DELETE FROM reports")
    pg_conn.commit()

# 데이터 삽입
inserted = 0
for r in reports:
    pg_cursor.execute('''
        INSERT INTO reports
        (complex_name, property_type, households, address, manager_name, contact,
         construction_types, assigned_company, recommended_company, status, notes,
         kcc_requests, photo_url, kapt_code, long_term_reserve, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        r.get("complex_name"), r.get("property_type"), r.get("households"),
        r.get("address"), r.get("manager_name"), r.get("contact"),
        r.get("construction_types"), r.get("assigned_company"), r.get("recommended_company"),
        r.get("status"), r.get("notes"), r.get("kcc_requests"),
        r.get("photo_url"), r.get("kapt_code"), r.get("long_term_reserve"),
        r.get("created_at"), r.get("updated_at")
    ))
    inserted += 1

pg_conn.commit()
pg_cursor.close()
pg_conn.close()

print(f"✅ PostgreSQL로 {inserted}건 이전 완료!")
