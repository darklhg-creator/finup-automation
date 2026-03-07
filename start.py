import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import time

# ==========================================
# 0. 사용자 설정
# ==========================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"
API_KEY = "62e0d95b35661ef8e1f9a665ef46cc7cd64a3ace4d179612dda40c847f6bdb7e"

KST_TIMEZONE = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST_TIMEZONE)
TARGET_DATE = CURRENT_KST.strftime("%Y-%m-%d")

# ==========================================
# 1. 공통 함수
# ==========================================
def send_discord_message(content):
    try:
        data = {'content': content}
        requests.post(DISCORD_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

# ==========================================
# 2. 날짜별 전체 종목 시세 한번에 가져오기
# ==========================================
def get_all_stocks_by_date(date_str):
    """특정 날짜의 전체 종목 시세를 한번에 가져오기"""
    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
    all_items = []
    page = 1

    while True:
        params = {
            "serviceKey": API_KEY,
            "numOfRows": "2000",
            "pageNo": str(page),
            "resultType": "json",
            "basDt": date_str
        }
        try:
            res = requests.get(url, params=params, timeout=15)
            data = res.json()
            body = data['response']['body']
            total = int(body['totalCount'])
            items = body['items']['item']

            if isinstance(items, dict):
                items = [items]

            all_items.extend(items)

            if page * 2000 >= total:
                break
            page += 1
            time.sleep(0.2)

        except Exception as e:
            print(f"날짜 {date_str} 데이터 오류: {e}")
            break

    return all_items

# ==========================================
# 3. 최근 20 거래일 날짜 리스트 구하기
# ==========================================
def get_recent_trading_dates(n=20):
    """최근 n개 거래일 날짜 리스트 반환"""
    dates = []
    date = CURRENT_KST

    # 오늘이 주말이거나 장 마감 전이면 어제부터
    if date.weekday() >= 5 or date.hour < 15 or (date.hour == 15 and date.minute < 30):
        date = date - timedelta(days=1)

    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"

    while len(dates) < n:
        date_str = date.strftime("%Y%m%d")
        params = {
            "serviceKey": API_KEY,
            "numOfRows": "1",
            "pageNo": "1",
            "resultType": "json",
            "basDt": date_str
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            total = int(data['response']['body']['totalCount'])
            if total > 0:
                dates.append(date_str)
        except:
            pass

        date = date - timedelta(days=1)
        time.sleep(0.1)

    return sorted(dates)

# ==========================================
# 4. 메인 로직
# ==========================================
def main():
    print(f"[{TARGET_DATE}] 프로그램 시작 (한국 시간 기준)")
    print("✅ 분석을 시작합니다...")

    try:
        # 최근 20 거래일 날짜 가져오기
        print("📅 최근 20 거래일 날짜 조회 중...")
        trading_dates = get_recent_trading_dates(20)
        print(f"✅ 거래일 확인: {trading_dates[0]} ~ {trading_dates[-1]}")

        # 날짜별로 전체 종목 데이터 수집
        print("📡 날짜별 전체 종목 시세 수집 중... (20번 호출)")
        date_data = {}
        for i, date_str in enumerate(trading_dates):
            print(f"  {i+1}/20 날짜 {date_str} 수집 중...")
            items = get_all_stocks_by_date(date_str)
            for item in items:
                code = item.get('srtnCd', '')
                market = item.get('mrktCtg', '')
                if market not in ['KOSPI', 'KOSDAQ']:
                    continue
                if code not in date_data:
                    date_data[code] = {
                        'name': item.get('itmsNm', ''),
                        'market': market,
                        'prices': []
                    }
                try:
                    price = float(str(item.get('clpr', '0')).replace(',', ''))
                    date_data[code]['prices'].append(price)
                except:
                    pass
            time.sleep(0.3)

        print(f"✅ 총 {len(date_data)}개 종목 데이터 수집 완료")

        # 이격도 계산
        all_analyzed = []
        for code, info in date_data.items():
            prices = info['prices']
            if len(prices) < 20:
                continue

            current_price = prices[-1]
            ma20 = sum(prices[-20:]) / 20

            if ma20 == 0:
                continue

            disparity = round((current_price / ma20) * 100, 1)
            all_analyzed.append({
                'name': info['name'],
                'code': code,
                'market': info['market'],
                'disparity': disparity
            })

        # KOSPI 500, KOSDAQ 1000으로 제한
        kospi = [r for r in all_analyzed if r['market'] == 'KOSPI'][:500]
        kosdaq = [r for r in all_analyzed if r['market'] == 'KOSDAQ'][:1000]
        all_analyzed = kospi + kosdaq

        # 계단식 필터링
        results = [r for r in all_analyzed if r['disparity'] <= 90.0]
        filter_level = "이격도 90% 이하 (초과대낙폭)"

        if not results:
            print("💡 90% 이하가 없어 95%로 범위를 넓힙니다.")
            results = [r for r in all_analyzed if r['disparity'] <= 95.0]
            filter_level = "이격도 95% 이하 (일반낙폭)"

        if results:
            results = sorted(results, key=lambda x: x['disparity'])

            report = f"### 📊 종목 분석 결과 ({filter_level})\n"
            for r in results[:40]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}%\n"

            report += "\n" + "="*30 + "\n"
            report += "📝 **[Check List]**\n"
            report += "1. 영업이익 적자기업 제외하고 테마별로 표로 분류\n"
            report += "2. 최근 일주일간 뉴스 및 날짜 확인\n"
            report += "3. 이격도 하락 원인 분석\n"
            report += "4. 종합 판단 후 최종 종목 선정"

            send_discord_message(report)
            print(f"✅ {len(results)}개 추출 및 전송 완료.")
        else:
            send_discord_message("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        err_msg = f"❌ 프로그램 오류: {e}"
        print(err_msg)
        send_discord_message(err_msg)

if __name__ == "__main__":
    main()
