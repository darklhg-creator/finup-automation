import requests

API_KEY = "62e0d95b35661ef8e1f9a665ef46cc7cd64a3ace4d179612dda40c847f6bdb7e"

# 공휴일 API 테스트
url = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"
params = {
    "serviceKey": API_KEY,
    "solYear": "2026",
    "solMonth": "03",
    "numOfRows": "20",
    "resultType": "json"
}
res = requests.get(url, params=params, timeout=10)
print("상태코드:", res.status_code)
print("응답:", res.text[:500])
