import requests
import json

API_KEY = "dcc614fd303886a1fcaf68d8ef0eb5720a321b324e84973ee83561c34f000bf3"

print("--- Test 1: AptBasisInfoService ---")
url1 = f"http://apis.data.go.kr/1613000/AptBasisInfoService/getAptList?serviceKey={API_KEY}&bjdceCd=41287&numOfRows=2&pageNo=1&_type=json"
res1 = requests.get(url1)
print(res1.status_code, res1.text[:200])

print("\n--- Test 2: URL decoding key ---")
url2 = f"http://apis.data.go.kr/1613000/AptBasisInfoService1/getAptList"
res2 = requests.get(url2, params={'serviceKey': requests.utils.unquote(API_KEY), 'bjdceCd':'41287'})
print(res2.status_code, res2.text[:200])

