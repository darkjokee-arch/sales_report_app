import sqlite3
import requests
import datetime
import json
import difflib
import time

DB_FILE = "sales_db.sqlite"
API_KEY = "dcc614fd303886a1fcaf68d8ef0eb5720a321b324e84973ee83561c34f000bf3"

# K-apt V2 Endpoints
API_URL_BID = "http://apis.data.go.kr/1613000/ApHusBidPblAncInfoOfferServiceV2/getPblAncDeSearchV2"
API_URL_RESULT = "http://apis.data.go.kr/1613000/ApHusBidResultNoticeInfoOfferServiceV2/getBidClosDeSearchV2"

# 도장 및 방수 공사에 관련된 키워드
TARGET_KEYWORDS = ["도장", "방수", "균열", "외벽", "지붕"]

def get_target_month():
    dt = datetime.datetime.now()
    if dt.year > 2024:
        dt = dt.replace(year=2024)
    return dt

def fetch_api_data(url):
    """K-apt 오픈 API에서 공고/결과를 가져옵니다."""
    dt = get_target_month()
    # 사용자의 요청에 따라 2025년 6월부터 2026년까지의 데이터를 조회
    bgngDe = "20250601"
    endDe = "20261231"
    
    params = {
        'serviceKey': API_KEY,
        'startDate': bgngDe,
        'endDate': endDe,
        'pageNo': '1',
        'numOfRows': '100',
        '_type': 'json'
    }
    
    print(f"[API Call] {url} (조회기간: {bgngDe}~{endDe})")
    
    try:
        response = requests.get(url, params=params, timeout=15)
        
        print(f"Raw Response: {response.text[:500]}")
        
        if response.status_code != 200:
            print(f"[Error] API 서버 오류: {response.status_code}")
            return []
            
        data = response.json()
        body = data.get("response", {}).get("body", {})
        raw_items = body.get("items", [])
        
        items = raw_items
        if isinstance(raw_items, dict):
            items = raw_items.get("item", [])
            
        if isinstance(items, dict):
            items = [items]
            
        print(f"[API Info] 총 {len(items)}건을 가져왔습니다.")
        return items
        
    except Exception as e:
        print(f"[Error] API 요청 중 예외 발생: {e}")
        return []

def get_mock_data():
    print("[Mock] 테스트용 목업 데이터를 사용합니다.")
    return [
       {
           "aptNm": "가좌마을1단지",
           "bjdceNm": "경기 고양시 일산서구 가좌동",
           "bidNtceNm": "가좌1단지 외부 도장 및 옥상 방수 공사",
           "bidNtceDt": "2026-03-20"
       },
       {
           "aptNm": "래미안 서초",
           "bjdceNm": "서울특별시 서초구 서초동",
           "bidNtceNm": "서초 래미안 조경 유지보수",
           "bidNtceDt": "2026-03-19"
       }
    ]

def normalize_text(text):
    """문자열의 공백 및 특수기호 제거, 소문자화 (유사도 비교용)"""
    if not text:
        return ""
    text = text.replace("아파트", "").replace("단지", "").replace(" ", "").strip()
    return text.lower()

def is_target_bid(bid_name):
    """공고명에 도장/방수 등 관련 키워드가 포함되었는지 확인"""
    if not bid_name: return False
    return any(keyword in bid_name for keyword in TARGET_KEYWORDS)

def sync_kapt_bids():
    """DB의 아파트들과 입찰/결과 공고를 매칭하고 상태를 업데이트"""
    
    bids = fetch_api_data(API_URL_BID)
    results = fetch_api_data(API_URL_RESULT)
    
    if not bids and not results:
        # API 오류 시 테스트용 데이터 사용
        bids = get_mock_data()
        
    target_bids = [b for b in bids if is_target_bid(b.get('bidNtceNm') or b.get('bidAncNm', ''))]
    target_results = [r for r in results if is_target_bid(r.get('bidNtceNm') or r.get('bidAncNm', ''))]
    
    if not target_bids and not target_results:
        print("[Sync] 매칭할 '도장/방수' 관련 공고/결과가 없습니다.")
        return
        
    print(f"[Sync] 도장/방수 입찰공고 {len(target_bids)}건, 결과공지 {len(target_results)}건 발견. 매칭 시작...")

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 처리할 보고서 가져오기
    cursor.execute("SELECT id, complex_name, address, status, notes FROM reports WHERE status != '타사공사완료'")
    reports = cursor.fetchall()
    
    matched_count = 0
    
    for report in reports:
        r_id = report["id"]
        r_name = normalize_text(report["complex_name"])
        r_address = report["address"]
        r_status = report["status"]
        
        # 1. 입찰결과공지 매칭 확인
        for res_item in target_results:
            b_name = normalize_text(res_item.get("aptNm", ""))
            if not b_name: continue
            
            # 주소의 시/군/구가 대략적으로라도 일치하는지 1차 확인
            b_address = res_item.get("bjdceNm", "")
            r_parts = str(r_address).split()
            b_parts = str(b_address).split()
            if not set(r_parts[:3]).intersection(set(b_parts[:3])): continue
            
            # 이름 유사도 비교 (80% 이상)
            if difflib.SequenceMatcher(None, r_name, b_name).ratio() >= 0.8:
                print(f"[Match Result 🔵] DB: {report['complex_name']} == K-apt: {res_item.get('aptNm')}")
                
                new_status = "계약완료"
                bid_summary = f"[입찰결과] 공고명: {res_item.get('bidNtceNm') or res_item.get('bidAncNm')} / 낙찰자: {res_item.get('scsbidEntrpsNm', '미상')}"
                new_notes = f"{report['notes']}\n{bid_summary}" if report["notes"] else bid_summary
                
                cursor.execute("UPDATE reports SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, new_notes, r_id))
                
                sys_msg = f"🎉 [시스템 알림] '{report['complex_name']}' 현장의 **입찰 결과**가 등록되었습니다!\n👉 {bid_summary}"
                cursor.execute("INSERT INTO chat_messages (sender_name, message, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)", ("시스템", sys_msg))
                
                matched_count += 1
                r_status = new_status # 업데이트 완료 표시
                break 

        # 2. 입찰공고 매칭 확인 (이미 계약완료 처리된 건은 스킵)
        if r_status != "계약완료":
            for bid in target_bids:
                b_name = normalize_text(bid.get("aptNm", ""))
                if not b_name: continue
                
                b_address = bid.get("bjdceNm", "")
                r_parts = str(r_address).split()
                b_parts = str(b_address).split()
                if not set(r_parts[:3]).intersection(set(b_parts[:3])): continue
                
                similarity = difflib.SequenceMatcher(None, r_name, b_name).ratio()
                if similarity >= 0.8:
                    print(f"[Match Bid 🟡] DB: {report['complex_name']} == K-apt: {bid.get('aptNm')} (유사도: {similarity:.2f})")
                    
                    new_status = "입찰예정"
                    bid_summary = f"[입찰공고] {bid.get('bidNtceDt', '')} 공고: {bid.get('bidNtceNm') or bid.get('bidAncNm')}"
                    new_notes = f"{report['notes']}\n{bid_summary}" if report["notes"] else bid_summary
                    
                    cursor.execute("UPDATE reports SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, new_notes, r_id))
                    
                    sys_msg = f"🔔 [시스템 알림] '{report['complex_name']}' 현장의 **입찰 공고**가 떴습니다!\n👉 공고명: {bid.get('bidNtceNm') or bid.get('bidAncNm')}\n상태를 확인해주세요."
                    cursor.execute("INSERT INTO chat_messages (sender_name, message, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)", ("시스템", sys_msg))
                    
                    matched_count += 1
                    break
                
    conn.commit()
    conn.close()
    print(f"[Sync Done] 총 {matched_count}건의 아파트가 K-apt 결과/공고와 성공적으로 매칭되어 업데이트되었습니다.")

if __name__ == "__main__":
    try:
        print("--- K-apt API 입찰공고/결과공지 스케줄러 동기화 시작 ---")
        sync_kapt_bids()
        print("--- 작동 완료 ---")
    except Exception as e:
        print(f"치명적인 오류 발생: {e}")
