import sqlite3
import requests
import datetime
import time

DB_FILE = "sales_db.sqlite"
API_KEY = "dcc614fd303886a1fcaf68d8ef0eb5720a321b324e84973ee83561c34f000bf3"

# K-apt API 엔드포인트
# 1. 단지기본정보 (주소로 단지코드 찾기용 - V3)
URL_BASIS = "http://apis.data.go.kr/1613000/AptListService3/getHsmpNmSearchV2"
# 2. 장기수선충당금 잔액조회 (V2)
URL_RESERVE = "http://apis.data.go.kr/1613000/AptRepairsCostServiceV2/getHsmpReserveBalanceInfoV2"

def format_currency(amount_str):
    if amount_str is None or str(amount_str).strip() == "None":
        return "0원"
    try:
        clean_amt = str(amount_str).replace(',', '').strip()
        return f"{int(clean_amt):,}원"
    except:
        return str(amount_str) + "원"

import difflib

BJDCE_MAPPING = {
    # 서울
    "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200", "광진구": "11215",
    "동대문구": "11230", "중랑구": "11260", "성북구": "11290", "강북구": "11305", "도봉구": "11320",
    "노원구": "11350", "은평구": "11380", "서대문구": "11410", "마포구": "11440", "양천구": "11470",
    "강서구": "11500", "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
    "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740",
    
    # 인천 (중복구명 처리를 위해 '인천 중구' 처럼 긴 이름 우선)
    "인천 중구": "28110", "인천 동구": "28140", "미추홀구": "28177", "연수구": "28185", "남동구": "28200",
    "부평구": "28237", "계양구": "28245", "인천 서구": "28260", "강화군": "28710", "옹진군": "28720",
    
    # 경기
    "수원시 장안구": "41111", "수원시 권선구": "41113", "수원시 팔달구": "41115", "수원시 영통구": "41117",
    "장안구": "41111", "권선구": "41113", "팔달구": "41115", "영통구": "41117",
    "성남시 수정구": "41131", "성남시 중원구": "41133", "성남시 분당구": "41135",
    "수정구": "41131", "중원구": "41133", "분당구": "41135",
    "의정부시": "41150", 
    "안양시 만안구": "41171", "안양시 동안구": "41173", "만안구": "41171", "동안구": "41173",
    "부천시": "41190", "광명시": "41210", "평택시": "41220", "동두천시": "41250",
    "안산시 상록구": "41271", "안산시 단원구": "41273", "상록구": "41271", "단원구": "41273",
    "고양시 덕양구": "41281", "고양시 일산동구": "41285", "고양시 일산서구": "41287",
    "덕양구": "41281", "일산동구": "41285", "일산서구": "41287",
    "과천시": "41290", "구리시": "41310", "남양주시": "41360", "오산시": "41370", "시흥시": "41390",
    "군포시": "41410", "의왕시": "41430", "하남시": "41450",
    "용인시 처인구": "41461", "용인시 기흥구": "41463", "용인시 수지구": "41465",
    "처인구": "41461", "기흥구": "41463", "수지구": "41465",
    "파주시": "41480", "이천시": "41500", "안성시": "41550", "김포시": "41570",
    "화성시": "41590", "광주시": "41610", "양주시": "41630", "포천시": "41650", "여주시": "41670",
    "연천군": "41800", "가평군": "41820", "양평군": "41830"
}

def get_real_kapt_code(address, complex_name):
    """주소에서 지역 단위 파악 후 단지목록 API로 실제 kaptCode 검색 (유사도 매칭 추가)"""
    bjdce_cd = "11650" # 기본값 서초구
    for key, val in BJDCE_MAPPING.items():
        if key in address:
            bjdce_cd = val
            break
            
    url = URL_BASIS
    params = {
        'serviceKey': API_KEY,
        'bjdceCd': bjdce_cd,
        'numOfRows': '1000',
        'pageNo': '1',
        '_type': 'json'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            body = data.get("response", {}).get("body", {})
            raw_items = body.get("items", [])
            
            items = raw_items
            if isinstance(raw_items, dict):
                items = raw_items.get("item", [])
                
            if isinstance(items, dict):
                items = [items]
            
            db_name = complex_name.replace('아파트', '').replace(' ', '')
            
            best_match_code = ""
            highest_ratio = 0.0
            
            for item in items:
                api_name = item.get('kaptName', '').replace('아파트', '').replace(' ', '')
                
                # 1. 완전 포함 관계
                if db_name in api_name or api_name in db_name:
                    return item.get('kaptCode')
                
                # 2. 유사도 측정 (가장 비슷한 단지 찾기용)
                ratio = difflib.SequenceMatcher(None, db_name, api_name).ratio()
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    best_match_code = item.get('kaptCode')
            
            # 유사도가 0.55 이상이면 꽤 비슷한 것으로 간주
            if highest_ratio > 0.55 and best_match_code:
                # print(f"  [유사도 매칭 {highest_ratio:.2f}] {db_name} -> API 예측 단지")
                return best_match_code
                    
    except Exception as e:
        print(f"[AptList Error] {e}")
    
    return ""

def get_reserve_balance(kapt_code):
    """kapt_code를 기반으로 장기수선충당금 잔액 조회"""
    if not kapt_code: return ""
    
    import datetime
    
    network_error = False
    
    # 최근 6개월 (이전 달부터 6개월 전까지) 역순 조회
    for i in range(1, 7):
        month = datetime.datetime.now().month - i
        year = datetime.datetime.now().year
        if month <= 0:
            month += 12
            year -= 1
        search_date = f"{year:04d}{month:02d}"
        
        params = {
            'serviceKey': API_KEY,
            'kaptCode': kapt_code,
            'searchDate': search_date,
            '_type': 'json'
        }
        
        print(f"[API Call] K-APT 코드 '{kapt_code}'의 {search_date}월 잔액 조회 중...")
        try:
            response = requests.get(URL_RESERVE, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                body = data.get("response", {}).get("body", {})
                
                item_data = body.get("item") or body.get("items", {}).get("item", [])
                
                if isinstance(item_data, dict):
                    items = [item_data]
                elif isinstance(item_data, list):
                    items = item_data
                else:
                    items = []
                
                if items:
                    amt = items[0].get('sTot')
                    if amt is None:
                        amt = items[0].get('lsbbmAmt')
                    
                    # 자료가 0이나 None이 아니면 즉시 리턴 (성공)
                    if amt and str(amt).strip() != "0" and str(amt).strip() != "None":
                        return format_currency(amt)
        except Exception as e:
            print(f"[Error] 잔액조회 API 요청 중 예외 발생 ({search_date}월): {e}")
            network_error = True
            
    # 6개월 모두 뒤졌는데 값이 없으면 미제출, 단 하나라도 네트워크 에러가 있었으면 조회 실패
    return "조회 실패" if network_error else "자료미제출"

def sync_reserve():
    print("--- K-apt 장기수선충당금 동기화 시작 ---")
    conn = sqlite3.connect(DB_FILE, timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, complex_name, address, kapt_code, long_term_reserve FROM reports")
    reports = [dict(row) for row in cursor.fetchall()]
    conn.close() # 네트워크 통신 중 DB 잠김(Lock)을 방지하기 위해 닫음
    
    updated_count = 0
    
    for row in reports:
        r_id = row['id']
        name = row['complex_name']
        address = row['address']
        k_code = row['kapt_code']
        reserve = row['long_term_reserve']
        
        # 1. 단지코드가 없으면 발급
        if not k_code:
            k_code = get_real_kapt_code(address, name)
            if k_code:
                # 쓰기 작업 시에만 잠깐씩 연결
                write_conn = sqlite3.connect(DB_FILE, timeout=10)
                write_cursor = write_conn.cursor()
                write_cursor.execute("UPDATE reports SET kapt_code = ? WHERE id = ?", (k_code, r_id))
                write_conn.commit()
                write_conn.close()
                print(f"[{name}] K-apt 단지코드 매핑 완료: {k_code}")
            
        # 2. 장기수선충당금이 비어있거나 업데이트가 필요하면 
        if not reserve or reserve in ["조회 전", "", "조회 실패", "자료미제출"]:
            balance = get_reserve_balance(k_code)
            if balance:
                write_conn = sqlite3.connect(DB_FILE, timeout=10)
                write_cursor = write_conn.cursor()
                write_cursor.execute("UPDATE reports SET long_term_reserve = ? WHERE id = ?", (balance, r_id))
                write_conn.commit()
                write_conn.close()
                print(f"[{name}] 장기수선충당금 업데이트 완료: {balance}")
                updated_count += 1
                
    print(f"\n[Sync Done] 총 {updated_count}개 단지의 장기수선충당금 잔액이 최신화되었습니다.")

import sys
if __name__ == "__main__":
    try:
        print("--- K-apt 장기수선충당금 동기화 시작 ---")
        sync_reserve()
        print("--- 작동 완료 ---")
    except Exception as e:
        print(f"치명적인 오류 발생: {e}")
    finally:
        if sys.stdout.isatty():
            input("\n창을 닫으려면 엔터 키를 누르세요...")
