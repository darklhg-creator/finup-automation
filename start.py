import requests

KRX_API_KEY = "5AB85D9D43EA4FAA9BC1907303BAFDC2C0377C5B"

# 올바른 KRX OpenAPI URL로 테스트
url = "https://openapi.krx.co.kr/contents/COM/GenerateOTP.jspx"
params = {
    "AUTH_KEY": KRX_API_KEY,
    "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
    "name": "fileDown",
    "filetype": "json"
}

res = requests.get(url, params=params, timeout=10)
print("상태코드:", res.status_code)
print("응답:", res.text[:500])
