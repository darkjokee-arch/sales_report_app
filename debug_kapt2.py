import requests

API_KEY = "dcc614fd303886a1fcaf68d8ef0eb5720a321b324e84973ee83561c34f000bf3"

url3 = "http://apis.data.go.kr/1613000/AptBidInfoService/getAptBidInfo"
params3 = {
    'serviceKey': API_KEY,
    'bidType': '1', # 공사
    '_type': 'json'
}
res3 = requests.get(url3, params=params3)
print("Bid API Status:", res3.status_code)
print("Bid API Response:", res3.text[:200])
