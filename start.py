import requests

API_KEY = "62e0d95b35661ef8e1f9a665ef46cc7cd64a3ace4d179612dda40c847f6bdb7e"

# 고객예탁금 테스트
url = "https://apis.data.go.kr/1160100/service/GetFSSInvstgInfoService/getInvstgTrnstnInfo"
params = {
    "serviceKey": API_KEY,
    "numOfRows": "5",
    "pageNo": "1",
    "resultType": "json"
}

res = requests.get(url, params=params, timeout=10)
print("상태코드:", res.status_code)
print("응답:", res.text[:500])
