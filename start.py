import requests

API_KEY = "62e0d95b35661ef8e1f9a665ef46cc7cd64a3ace4d179612dda40c847f6bdb7e"
url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"

# 파라미터 이름 확인용
params = {
    "serviceKey": API_KEY,
    "numOfRows": "3",
    "pageNo": "1",
    "resultType": "json",
    "basDt": "20260305",
    "likeSrtnCd": "156100"  # srtnCd 대신 likeSrtnCd 시도
}
res = requests.get(url, params=params, timeout=10)
data = res.json()
items = data['response']['body']['items']['item']
if isinstance(items, dict):
    items = [items]
for item in items:
    print(f"날짜: {item.get('basDt')}, 종목: {item.get('itmsNm')}, 종가: {item.get('clpr')}")
