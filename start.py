import requests

API_KEY = "62e0d95b35661ef8e1f9a665ef46cc7cd64a3ace4d179612dda40c847f6bdb7e"

# 금융투자협회종합통계 여러 URL 테스트
urls = [
    "https://apis.data.go.kr/1160100/service/GetFssComdStatService/getInvstgTrnstnInfo",
    "https://apis.data.go.kr/1160100/service/GetFssComdStatService/getCustDpstInfo",
    "https://apis.data.go.kr/1160100/service/GetKofiaStatService/getCustDpstInfo",
    "https://apis.data.go.kr/1160100/service/GetKofiaStatService/getInvstgTrnstnInfo",
]

for url in urls:
    params = {
        "serviceKey": API_KEY,
        "numOfRows": "1",
        "pageNo": "1",
        "resultType": "json"
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        print(f"URL: {url.split('/')[-2]}/{url.split('/')[-1]}")
        print(f"상태코드: {res.status_code}, 응답: {res.text[:100]}")
        print()
    except Exception as e:
        print(f"오류: {e}")
