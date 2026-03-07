import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import time
import zipfile
import io

# ==========================================
# 0. 사용자 설정
# ==========================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"
API_KEY = "62e0d95b35661ef8e1f9a665ef46cc7cd64a3ace4d179612dda40c847f6bdb7e"
DART_API_KEY = "732bd7e69779f5735f3b9c6aae3c4140f7841c3e"

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
# 2. 휴장일 체크
# ==========================================
def is_holiday():
    if CURRENT_KST.weekday() >= 5:
        return True
    today_str = CURRENT_KST.strftime("%Y%m%d")
    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
    params = {
        "serviceKey": API_KEY,
        "numOfRows": "1",
        "pageNo": "1",
        "resultType": "json",
        "basDt": today_str
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        total = int(data['response']['body']['totalCount'])
        if total == 0:
            return True
    except:
        pass
    return False

# ==========================================
# 3. DART 재무정보 ZIP으로 한번에 가져오기
# ==========================================
def get_profit_dict():
    """DART 재무정보 일괄다운로드로 전체 기업 영업이익 한번에 가져오기"""
    print("📊 DART 전체 기업 영업이익 수집 중...")
    profit_dict = {}
    target_year = str(CURRENT_KST.year - 1)

    url = "https://opendart.fss.or.kr/api/fnlttXbrlDs002.xml"
    params = {
        "crtfc_key": DART_API_KEY,
        "bsns_year": target_year,
        "reprt_code": "11011"
    }

    try:
        res = requests.get(url, params=params, timeout=60)
        zf = zipfile.ZipFile(io.BytesIO(res.content))
        print(f"✅ ZIP 파일 수신 완료, 파일 목록: {zf.namelist()}")

        for fname in zf.namelist():
            if fname.endswith('.csv') or fname.endswith('.tsv'):
                with zf.open(fname) as f:
                    try:
                        df = pd.read_csv(f, encoding='utf-8', sep='\t' if fname.endswith('.tsv') else ',')
                    except:
                        f.seek(0)
                        df = pd.read_csv(f, encoding='cp949', sep='\t' if fname.endswith('.tsv') else ',')

                    print(f"파일: {fname}, 컬럼: {list(df.columns)[:5]}")

                    # 영업이익 행 찾기
                    for col in df.columns:
                        if '계정' in col or 'account' in col.lower():
                            acct_col = col
                            break
                    else:
                        continue

                    stock_col = None
                    for col in df.columns:
                        if '종목' in col or 'stock' in col.lower():
                            stock_col = col
                            break

                    amount_col = None
                    for col in df.columns:
                        if '당기' in col or 'amount' in col.lower():
                            amount_col = col
                            break

                    if not stock_col or not amount_col:
                        continue

                    df_profit = df[df[acct_col].str.contains('영업이익', na=False)]
                    for _, row in df_profit.iterrows():
                        code = str(row.get(stock_col, '')).strip().zfill(6)
                        try:
                            amount_str = str(row.get(amount_col, '0')).replace(',', '').strip()
                            if amount_str in ['', '-', 'nan']:
                                amount_str = '0'
                            amount = int(float(amount_str))
                            if code not in profit_dict:
                                profit_dict[code] = '흑자' if amount > 0 else '적자'
                        except:
                            pass

    except Exception as e:
        print(f"DART ZIP 수집 오류: {e}")

    print(f"✅ 영업이익 데이터 {len(profit_dict)}개 종목 완료")
    return profit_dict

# ==========================================
# 4. 날짜별 전체 종목 시세 한번에 가져오기
# ==========================================
def get_all_stocks_by_date(date_str):
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
# 5. 최근 20 거래일 날짜 리스트 구하기
# ==========================================
def get_recent_trading_dates(n=20):
    dates = []
    date = CURRENT_KST

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
# 6. 메인 로직
# ==========================================
def main():
    print(f"[{TARGET_DATE}] 프로그램 시작 (한국 시간 기준)")

    # 휴장일 체크
    #if is_holiday():
    #    msg = f"⏹️ [{TARGET_DATE}] 오늘은 휴장일입니다."
    #    print(msg)
    #    send_discord_message(msg)
    #    return

    print("✅ 분석을 시작합니다...")

    try:
        # DART 영업이익 먼저 수집
        profit_dict = get_profit_dict()

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

            profit_status = profit_dict.get(code, '')
            if profit_status == '흑자':
                profit_label = '[흑자]'
            elif profit_status == '적자':
                profit_label = '[적자]'
            else:
                profit_label = ''

            all_analyzed.append({
                'name': info['name'],
                'code': code,
                'market': info['market'],
                'disparity': disparity,
                'profit_label': profit_label
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
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}% {r['profit_label']}\n"

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
