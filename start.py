import FinanceDataReader as fdr
import requests
import pandas as pd
import zipfile
import io
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# ==========================================
# 0. 사용자 설정
# ==========================================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"
API_KEY = "62e0d95b35661ef8e1f9a665ef46cc7cd64a3ace4d179612dda40c847f6bdb7e"
DART_API_KEY = "732bd7e69779f5735f3b9c6aae3c4140f7841c3e"
KRX_API_KEY = "5AB85D9D43EA4FAA9BC1907303BAFDC2C0377C5B"

KST_TIMEZONE = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST_TIMEZONE)
TARGET_DATE = CURRENT_KST.strftime("%Y-%m-%d")
start_date = (CURRENT_KST - timedelta(days=60)).strftime("%Y-%m-%d")

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
# 2. 휴장일 체크 (주말만)
# ==========================================
def is_holiday():
    if CURRENT_KST.weekday() >= 5:
        return True
    return False

# ==========================================
# 3. 종목 리스트 가져오기
# ==========================================
def get_stock_list():
    print("📡 종목 리스트 불러오는 중...")
    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
    rows = []

    date = CURRENT_KST
    recent_date = None
    for _ in range(10):
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
                recent_date = date_str
                break
        except:
            pass
        date = date - timedelta(days=1)
        time.sleep(0.1)

    if not recent_date:
        raise Exception("최근 거래일을 찾을 수 없습니다.")

    print(f"📅 기준 거래일: {recent_date}")

    for market in ["KOSPI", "KOSDAQ"]:
        max_stocks = 500 if market == "KOSPI" else 1000
        page = 1
        market_rows = []
        while len(market_rows) < max_stocks:
            params = {
                "serviceKey": API_KEY,
                "numOfRows": "2000",
                "pageNo": str(page),
                "resultType": "json",
                "basDt": recent_date,
                "mrktCls": market
            }
            try:
                res = requests.get(url, params=params, timeout=15)
                data = res.json()
                body = data['response']['body']
                total = int(body['totalCount'])
                items = body['items']['item']
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    market_rows.append({
                        'Code': item.get('srtnCd', ''),
                        'Name': item.get('itmsNm', ''),
                        'Market': market
                    })
                if page * 2000 >= total:
                    break
                page += 1
                time.sleep(0.2)
            except Exception as e:
                print(f"종목 리스트 오류: {e}")
                break
        rows.extend(market_rows[:max_stocks])

    df = pd.DataFrame(rows)
    print(f"✅ 총 {len(df)}개 종목 로드 완료")
    return df

# ==========================================
# 4. KRX 관리종목/거래정지 필터
# ==========================================
def get_krx_filter():
    print("📡 KRX 관리종목/거래정지 조회 중...")
    exclude_codes = set()
    recent_date = None

    # 최근 거래일 찾기
    date = CURRENT_KST
    for _ in range(10):
        date_str = date.strftime("%Y%m%d")
        for api in ["sto/stk_bydd_trd", "sto/ksq_bydd_trd"]:
            url = f"https://data-dbg.krx.co.kr/svc/apis/{api}"
            headers = {"AUTH_KEY": KRX_API_KEY}
            params = {"basDd": date_str}
            try:
                res = requests.get(url, params=params, headers=headers, timeout=10)
                data = res.json()
                if data.get('OutBlock_1'):
                    recent_date = date_str
                    break
            except:
                pass
        if recent_date:
            break
        date = date - timedelta(days=1)
        time.sleep(0.1)

    if not recent_date:
        print("⚠️ KRX 데이터 조회 실패, 필터 건너뜀")
        return exclude_codes

    print(f"📅 KRX 기준일: {recent_date}")

    for api, market in [
        ("sto/ksq_bydd_trd", "KOSDAQ"),
        ("sto/stk_bydd_trd", "KOSPI")
    ]:
        url = f"https://data-dbg.krx.co.kr/svc/apis/{api}"
        headers = {"AUTH_KEY": KRX_API_KEY}
        params = {"basDd": recent_date}
        try:
            res = requests.get(url, params=params, headers=headers, timeout=10)
            data = res.json()
            for item in data.get('OutBlock_1', []):
                code = item.get('ISU_CD', '')
                sect = item.get('SECT_TP_NM', '').strip()
                volume = item.get('ACC_TRDVOL', '0')

                # 관리종목 제외
                if '관리' in sect:
                    exclude_codes.add(code)

                # 거래정지 제외 (거래량 0)
                try:
                    if int(volume) == 0:
                        exclude_codes.add(code)
                except:
                    pass

        except Exception as e:
            print(f"KRX {market} 조회 오류: {e}")

    print(f"✅ KRX 필터 완료: {len(exclude_codes)}개 제외 대상")
    return exclude_codes

# ==========================================
# 5. DART corp_code 매핑
# ==========================================
def get_corp_code_map():
    print("📡 DART 기업코드 매핑 중...")
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    params = {"crtfc_key": DART_API_KEY}
    res = requests.get(url, params=params, timeout=30)
    z = zipfile.ZipFile(io.BytesIO(res.content))
    xml_data = z.read('CORPCODE.xml')
    root = ET.fromstring(xml_data)
    stock_to_corp = {}
    for item in root.findall('list'):
        stock_code = item.findtext('stock_code', '').strip()
        corp_code = item.findtext('corp_code', '').strip()
        if stock_code:
            stock_to_corp[stock_code] = corp_code
    print(f"✅ {len(stock_to_corp)}개 기업코드 매핑 완료")
    return stock_to_corp

# ==========================================
# 6. 영업이익 + 부채비율 조회
# ==========================================
def get_dart_info(corp_code):
    """영업이익(흑자여부)과 부채비율 반환"""
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
    for reprt_code in ["11011", "11014"]:
        params = {
            "crtfc_key": DART_API_KEY,
            "corp_code": corp_code,
            "bsns_year": "2024",
            "reprt_code": reprt_code
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            data = res.json()
            if data.get('status') != '000':
                continue

            operating_profit = None
            total_assets = None
            total_liabilities = None

            for item in data['list']:
                sj = item.get('sj_div', '')
                account = item.get('account_nm', '')
                amount_str = item.get('thstrm_amount', '0').replace(',', '').replace(' ', '')

                try:
                    amount = int(amount_str) if amount_str else None
                except:
                    amount = None

                # 영업이익
                if sj == 'IS' and account == '영업이익':
                    operating_profit = amount

                # 자산총계 / 부채총계
                if sj == 'BS' and account == '자산총계':
                    total_assets = amount
                if sj == 'BS' and account == '부채총계':
                    total_liabilities = amount

            # 부채비율 계산 (부채/자본 = 부채/(자산-부채))
            debt_ratio = None
            if total_assets and total_liabilities:
                equity = total_assets - total_liabilities
                if equity > 0:
                    debt_ratio = round((total_liabilities / equity) * 100, 1)

            return operating_profit, debt_ratio

        except:
            continue

    return None, None

# ==========================================
# 7. 이격도 계산 (멀티스레딩용)
# ==========================================
def fetch_disparity(row):
    code = row['Code']
    name = row['Name']
    market = row['Market']
    try:
        df = fdr.DataReader(code, start_date)
        if len(df) < 20:
            return None

        # 거래량 필터 (최근 20일 평균 거래량 10만주 이하 제외)
        avg_volume = sum(df['Volume'].tolist()[-20:]) / 20
        if avg_volume < 100000:
            return None

        closes = df['Close'].tolist()
        current_price = closes[-1]
        ma20 = sum(closes[-20:]) / 20
        if ma20 == 0:
            return None

        disparity = round((current_price / ma20) * 100, 2)
        return {
            'name': name,
            'code': code,
            'market': market,
            'disparity': disparity
        }
    except:
        return None

# ==========================================
# 8. 지수 이격도
# ==========================================
def get_index_disparity():
    print("📈 코스피/코스닥 지수 이격도 계산 중...")
    result = {}
    for code, name in [("^KS11", "KOSPI"), ("^KQ11", "KOSDAQ")]:
        try:
            df = fdr.DataReader(code, start_date)
            if len(df) < 20:
                result[name] = None
                continue
            closes = df['Close'].tolist()
            current = closes[-1]
            ma20 = sum(closes[-20:]) / 20
            disparity = round((current / ma20) * 100, 2)
            result[name] = disparity
            print(f"✅ {name} 이격도: {disparity}%")
        except Exception as e:
            print(f"{name} 지수 오류: {e}")
            result[name] = None
    return result

def get_index_comment(name, disparity):
    if disparity is None:
        return f"· {name}: 데이터 없음"
    elif disparity >= 110:
        return f"· {name}: {disparity}% ⚠️ 시장이 과열되었습니다. 비중 조절해주세요"
    elif disparity <= 80:
        return f"· {name}: {disparity}% ✅ 비중을 늘려도 될 타이밍입니다"
    else:
        return f"· {name}: {disparity}% 📊 보통 수준입니다"

# ==========================================
# 9. 메인 로직
# ==========================================
def main():
    print(f"[{TARGET_DATE}] 프로그램 시작 (한국 시간 기준)")

    if is_holiday():
        msg = f"⏹️ [{TARGET_DATE}] 오늘은 휴장일입니다."
        print(msg)
        send_discord_message(msg)
        return

    print("✅ 분석을 시작합니다...")

    try:
        # 종목 리스트
        df_list = get_stock_list()
        if df_list.empty:
            raise Exception("종목 리스트가 비어있습니다.")

        # KRX 관리종목/거래정지 필터
        krx_exclude = get_krx_filter()

        # KRX 필터 적용
        before = len(df_list)
        df_list = df_list[~df_list['Code'].isin(krx_exclude)]
        print(f"✅ KRX 필터 후: {before}개 → {len(df_list)}개")

        # DART 기업코드 매핑
        corp_map = get_corp_code_map()

        # 멀티스레딩으로 이격도 분석
        total_len = len(df_list)
        print(f"📡 총 {total_len}개 종목 분석 시작... (멀티스레딩 5개)")
        all_analyzed = []
        completed = 0

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_disparity, row): row for _, row in df_list.iterrows()}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_analyzed.append(result)
                completed += 1
                if completed % 100 == 0:
                    print(f"  진행중... {completed}/{total_len}")

        print(f"✅ {len(all_analyzed)}개 종목 분석 완료")

        # 계단식 필터링
        results = [r for r in all_analyzed if r['disparity'] <= 90.0]
        filter_level = "이격도 90% 이하 (초과대낙폭)"

        if not results:
            print("💡 90% 이하가 없어 95%로 범위를 넓힙니다.")
            results = [r for r in all_analyzed if r['disparity'] <= 95.0]
            filter_level = "이격도 95% 이하 (일반낙폭)"

        results = sorted(results, key=lambda x: x['disparity'])

        # DART 적자/부채비율 필터
        print(f"📊 DART 영업이익/부채비율 조회 중... ({len(results)}개 종목)")
        profit_results = []
        excluded_profit = 0
        excluded_debt = 0
        no_data = 0

        for r in results:
            corp_code = corp_map.get(r['code'])
            if not corp_code:
                no_data += 1
                profit_results.append(r)
                continue

            profit, debt_ratio = get_dart_info(corp_code)

            if profit is None:
                no_data += 1
                profit_results.append(r)
            elif profit <= 0:
                excluded_profit += 1
                print(f"  ❌ 적자 제외: {r['name']}({r['code']})")
            elif debt_ratio and debt_ratio > 200:
                excluded_debt += 1
                print(f"  ❌ 부채비율 제외: {r['name']}({r['code']}) {debt_ratio}%")
            else:
                profit_results.append(r)

            time.sleep(0.2)

        print(f"✅ 적자 제외: {excluded_profit}개, 부채비율 제외: {excluded_debt}개, 데이터없음: {no_data}개, 최종: {len(profit_results)}개")

        # 지수 이격도
        index_disparity = get_index_disparity()

        if profit_results:
            report = "📈 **[시장 이격도]**\n"
            report += get_index_comment("KOSPI", index_disparity.get('KOSPI')) + "\n"
            report += get_index_comment("KOSDAQ", index_disparity.get('KOSDAQ')) + "\n"

            report += "\n" + "="*30 + "\n"
            report += f"### 📊 종목 분석 결과 ({filter_level} / 흑자+부채비율200%이하)\n"
            for r in profit_results[:50]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}%\n"

            report += "\n" + "="*30 + "\n"
            report += "📝 **[Check List]**\n"
            report += "1. 영업이익 적자기업 제외하고 테마별로 표로 분류\n"
            report += "2. 최근 일주일간 뉴스 및 날짜 확인\n"
            report += "3. 이격도 하락 원인 분석\n"
            report += "4. 펀더멘탈 거버넌스 벨류에이션 및 최근 일주일간 호재와 강세섹터 종합 판단 후 최종 종목 선정\n"

            send_discord_message(report)
            print(f"✅ {len(profit_results)}개 추출 및 전송 완료.")
        else:
            send_discord_message("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        err_msg = f"❌ 프로그램 오류: {e}"
        print(err_msg)
        send_discord_message(err_msg)

if __name__ == "__main__":
    main()
