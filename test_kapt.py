import requests

API_KEY = 'dcc614fd303886a1fcaf68d8ef0eb5720a321b324e84973ee83561c34f000bf3'
url = 'http://apis.data.go.kr/1613000/AptBidInfoService/getAptBidInfo'

params = {
    'serviceKey': API_KEY,
    'bidNtceBgngDt': '202603',
    'bidNtceNm': '도장',
    'pageNo': '1',
    'numOfRows': '10'
}

print(f"Requesting: {url}")
try:
    response = requests.get(url, params=params)
    print("Status Code:", response.status_code)
    print(response.text[:1000])
except Exception as e:
    print("Error:", e)
