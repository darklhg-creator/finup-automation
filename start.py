import requests

KRX_API_KEY = "5AB85D9D43EA4FAA9BC1907303BAFDC2C0377C5B"

# 고객예탁금 테스트
url = "https://openapi.krx.co.kr/contents/COM/GenerateOTP.jspx"
params = {
    "AUTH_KEY": KRX_API_KEY,
    "bld": "dbms/MDC/STAT/standard/MDCSTAT03901",
    "name": "fileDown",
    "filetype": "json"
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

res = requests.get(url, params=params, headers=headers, timeout=10)
print("상태코드:", res.status_code)
print("응답:", res.text[:500])
