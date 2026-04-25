import sys
import os
import sqlite3
import pandas as pd

FILE_PATH = "2027년예정_도장및방수공사수요_260424.xlsx"
DB_PATH = "sales_db.sqlite"
TARGET_YEAR = 2027

SHEET_TYPE_MAP = {
    "내부": "내부도장",
    "지하주차장": "지하주차장 바닥도색",
    "외부": "균열보수 및 재도장",
    "옥상방수": "옥상방수",
}


def determine_company_by_address(address: str) -> str:
    addr = address.replace(" ", "")
    seil_keywords = ["서대문구", "마포구", "은평구", "종로구", "중구", "동작구", "용산구",
                     "강서구", "양천구", "구로구", "파주시", "김포시", "부천시", "인천"]
    sejin_keywords = ["서초구", "강남구", "관악구", "금천구", "영등포구",
                      "과천시", "성남시", "분당구", "안양시", "수원시", "용인시"]
    theseum_keywords = ["일산", "고양시", "덕양구", "의정부시", "양주시", "도봉구", "강북구"]
    unid_keywords = ["하남시", "구리시", "남양주", "송파구", "강동구", "광진구",
                     "성동구", "동대문구", "중랑구", "노원구"]
    for kw in seil_keywords:
        if kw in addr: return "세일산업개발"
    for kw in sejin_keywords:
        if kw in addr: return "세진씨엔씨"
    for kw in theseum_keywords:
        if kw in addr: return "더세움"
    for kw in unid_keywords:
        if kw in addr: return "유니드건설"
    return "미정"


def normalize_contact(raw) -> str:
    contact = str(raw).strip() if pd.notna(raw) else ""
    if contact.endswith(".0"):
        contact = contact[:-2]
    if len(contact) == 9 and not contact.startswith("0"):
        contact = "0" + contact
    return contact


def load_sheets():
    """4개 시트를 읽어 단지 단위로 통합. 키=(단지명, 연락처)."""
    aggregated = {}
    xls = pd.read_excel(FILE_PATH, sheet_name=None, header=1)

    for sheet_name, const_type in SHEET_TYPE_MAP.items():
        if sheet_name not in xls:
            print(f"[경고] 시트 '{sheet_name}' 없음, 스킵")
            continue
        df = xls[sheet_name]
        for _, row in df.iterrows():
            c_name = str(row.iloc[0]).strip()
            if c_name.lower() == "nan" or not c_name:
                continue
            households = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
            contact = normalize_contact(row.iloc[2])
            address = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
            manager = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ""

            key = (c_name, contact)
            if key in aggregated:
                aggregated[key]["types"].add(const_type)
            else:
                aggregated[key] = {
                    "complex_name": c_name,
                    "households": households,
                    "contact": contact,
                    "address": address,
                    "manager": manager,
                    "types": {const_type},
                }
    return aggregated


def main():
    if not os.path.exists(FILE_PATH):
        print(f"파일 없음: {FILE_PATH}")
        sys.exit(1)

    aggregated = load_sheets()
    print(f"통합 단지 수: {len(aggregated)}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted = 0
    skipped = 0
    for key, data in aggregated.items():
        c_name, contact = key
        # 동일 (단지, 연락처, 연도) 중복 방지
        cursor.execute(
            "SELECT id FROM reports WHERE complex_name = ? AND contact = ? AND target_year = ?",
            (c_name, contact, TARGET_YEAR),
        )
        if cursor.fetchone():
            skipped += 1
            continue

        const_types = ", ".join(sorted(data["types"]))
        recommended = determine_company_by_address(data["address"])
        cursor.execute(
            """
            INSERT INTO reports
            (complex_name, property_type, households, address, manager_name, contact,
             construction_types, assigned_company, recommended_company, status, notes, target_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                c_name, "아파트/오피스텔", data["households"], data["address"],
                data["manager"], contact, const_types, "미정", recommended,
                "방문전", "", TARGET_YEAR,
            ),
        )
        inserted += 1

    conn.commit()

    cursor.execute("SELECT target_year, COUNT(*) FROM reports GROUP BY target_year")
    print("연도별:", cursor.fetchall())
    conn.close()

    print(f"INSERT: {inserted} / SKIP(중복): {skipped}")


if __name__ == "__main__":
    main()
