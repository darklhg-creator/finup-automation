import requests

KRX_API_KEY = "5AB85D9D43EA4FAA9BC1907303BAFDC2C0377C5B"

# 고객예탁금 테스트
url = "http://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"
params = {
    "basDd": "20260306"
}
headers = {
    "AUTH_KEY": KRX_API_KEY
}

res = requests.get(url, params=params, headers=headers, timeout=10)
print("상태코드:", res.status_code)
print("응답:", res.text[:500])
