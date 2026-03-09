import requests

KRX_API_KEY = "5AB85D9D43EA4FAA9BC1907303BAFDC2C0377C5B"

# 코스피 종목 시세 테스트
url = "http://data-dbg.krx.co.kr/svc/apis/sto/stk_bydd_trd"
params = {
    "AUTH_KEY": KRX_API_KEY,
    "BAS_DD": "20260306"
}

res = requests.get(url, params=params, timeout=10)
print("상태코드:", res.status_code)
print("응답:", res.text[:500])
