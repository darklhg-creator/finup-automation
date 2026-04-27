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
BSNS_YEAR = str(CURRENT_KST.year - 2)

# ==========================================
# 1. 디스코드 전송
# ==========================================
def send_discord_message(content):
    try:
        data = {'content': content}
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        print(f"디스코드 전송: 상태코드 {response.status_code} / {len(content)}자")
        if response.status_code not in (200, 204):
            print(f"  ⚠️ 응답 내용: {response.text}")
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

# ==========================================
# 2. 휴장일 체크
# ==========================================
def is_holiday():
    return CURRENT_KST.weekday() >= 5

# ==========================================
# 3. 종목 리스트
# ==========================================
def get_stock_list():
    print("📡 종목 리스트 불러오는 중...")
    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
    rows = []

    date = CURRENT_KST
    recent_date = None
    for _ in range(10):
        date_str = date.strftime("%Y%m%d")
        params = {"serviceKey": API_KEY, "numOfRows": "1", "pageNo": "1", "resultType": "json", "basDt": date_str}
        try:
            res = requests.get(url, params=params, timeout=10)
            if int(res.json()['response']['body']['totalCount']) > 0:
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
        max_stocks = 1000
        page = 1
        market_rows = []
        while len(market_rows) < max_stocks:
            params = {"serviceKey": API_KEY, "numOfRows": "2000", "pageNo": str(page),
                      "resultType": "json", "basDt": recent_date, "mrktCls": market}
            try:
                res = requests.get(url, params=params, timeout=15)
                body = res.json()['response']['body']
                total = int(body['totalCount'])
                items = body['items']['item']
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    market_rows.append({'Code': item.get('srtnCd', ''), 'Name': item.get('itmsNm', ''), 'Market': market})
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
    date = CURRENT_KST
    recent_date = None
    for _ in range(10):
        date_str = date.strftime("%Y%m%d")
        try:
            res = requests.get("https://data-dbg.krx.co.kr/svc/apis/sto/ksq_bydd_trd",
                               params={"basDd": date_str}, headers={"AUTH_KEY": KRX_API_KEY}, timeout=10)
            if res.json().get('OutBlock_1'):
                recent_date = date_str
                break
        except:
            pass
        date = date - timedelta(days=1)
        time.sleep(0.1)

    if not recent_date:
        print("⚠️ KRX 데이터 조회 실패, 필터 건너뜀")
        return exclude_codes
    print(f"📅 KRX 기준일: {recent_date}")

    for api, market in [("sto/stk_bydd_trd", "KOSPI"), ("sto/ksq_bydd_trd", "KOSDAQ")]:
        try:
            res = requests.get(f"https://data-dbg.krx.co.kr/svc/apis/{api}",
                               params={"basDd": recent_date}, headers={"AUTH_KEY": KRX_API_KEY}, timeout=10)
            for item in res.json().get('OutBlock_1', []):
                code = item.get('ISU_CD', '')
                if '관리' in item.get('SECT_TP_NM', '').strip():
                    exclude_codes.add(code)
                try:
                    if int(item.get('ACC_TRDVOL', '0')) == 0:
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
    res = requests.get("https://opendart.fss.or.kr/api/corpCode.xml",
                       params={"crtfc_key": DART_API_KEY}, timeout=30)
    z = zipfile.ZipFile(io.BytesIO(res.content))
    root = ET.fromstring(z.read('CORPCODE.xml'))
    stock_to_corp = {}
    for item in root.findall('list'):
        stock_code = item.findtext('stock_code', '').strip()
        corp_code = item.findtext('corp_code', '').strip()
        if stock_code:
            stock_to_corp[stock_code] = corp_code
    print(f"✅ {len(stock_to_corp)}개 기업코드 매핑 완료")
    return stock_to_corp

# ==========================================
# 6. DART 영업이익 조회
# ==========================================
def get_dart_info(corp_code):
    for reprt_code in ["11011", "11014"]:
        try:
            res = requests.get("https://opendart.fss.or.kr/api/fnlttSinglAcnt.json", params={
                "crtfc_key": DART_API_KEY, "corp_code": corp_code,
                "bsns_year": BSNS_YEAR, "reprt_code": reprt_code
            }, timeout=10)
            data = res.json()
            if data.get('status') != '000':
                continue

            operating_income = None
            for item in data['list']:
                sj = item.get('sj_div', '')
                account = item.get('account_nm', '')
                try:
                    amount = int(item.get('thstrm_amount', '0').replace(',', '').replace(' ', ''))
                except:
                    amount = None
                if sj == 'IS' and '영업이익' in account:
                    operating_income = amount

            return operating_income
        except:
            continue

    return None

# ==========================================
# 7. 고객예탁금 + 신용잔고
# ==========================================
def get_market_capital_info():
    print("💰 고객예탁금/신용잔고 조회 중...")
    base = "https://apis.data.go.kr/1160100/service/GetKofiaStatisticsInfoService"
    try:
        res = requests.get(base + "/getSecuritiesMarketTotalCapitalInfo",
                           params={"serviceKey": API_KEY, "numOfRows": "2", "pageNo": "1", "resultType": "json"}, timeout=10)
        deposit_raw = res.json()['response']['body']['items']['item']
        deposit_data = sorted(deposit_raw if isinstance(deposit_raw, list) else [deposit_raw],
                              key=lambda x: x['basDt'], reverse=True)

        res = requests.get(base + "/getGrantingOfCreditBalanceInfo",
                           params={"serviceKey": API_KEY, "numOfRows": "2", "pageNo": "1", "resultType": "json"}, timeout=10)
        credit_raw = res.json()['response']['body']['items']['item']
        credit_data = sorted(credit_raw if isinstance(credit_raw, list) else [credit_raw],
                             key=lambda x: x['basDt'], reverse=True)

        today_deposit = int(deposit_data[0]['invrDpsgAmt'])
        today_credit = int(credit_data[0]['crdTrFingWhl'])
        prev_credit = int(credit_data[1]['crdTrFingWhl']) if len(credit_data) > 1 else None
        credit_ratio = round((today_credit / today_deposit) * 100, 2)
        credit_change = round((today_credit - prev_credit) / prev_credit * 100, 2) if prev_credit else None
        print(f"✅ 고객예탁금: {today_deposit/1e12:.1f}조, 신용잔고: {today_credit/1e12:.1f}조, 비율: {credit_ratio}%")
        return {'deposit': today_deposit, 'credit': today_credit, 'credit_ratio': credit_ratio, 'credit_change': credit_change}
    except Exception as e:
        print(f"고객예탁금/신용잔고 조회 오류: {e}")
        return None

def get_capital_comment(info):
    if info is None:
        return "· 고객예탁금/신용잔고: 데이터 없음\n"
    ratio = info['credit_ratio']
    change = info['credit_change']
    ratio_comment = (f"{ratio}% ✅ 안전 (레버리지 낮음)" if ratio <= 20 else
                     f"{ratio}% 📊 보통" if ratio <= 25 else
                     f"{ratio}% ⚠️ 주의 (레버리지 과다)" if ratio <= 30 else
                     f"{ratio}% 🚨 위험 (폭락장 전조 가능성)")
    change_comment = ("전일대비: 데이터 없음" if change is None else
                      f"전일대비: {change}% 🚨 급감 (반대매매 위험)" if change <= -4 else
                      f"전일대비: {change}% ⚠️ 주의" if change <= -2 else
                      f"전일대비: {change}% ⚠️ 레버리지 증가" if change >= 2 else
                      f"전일대비: {change}% 📊 보통")
    return (f"· 고객예탁금: {info['deposit']/1e12:.1f}조 / 신용잔고: {info['credit']/1e12:.1f}조\n"
            f"· 신용잔고/예탁금 비율: {ratio_comment}\n"
            f"· 신용잔고 {change_comment}\n")

# ==========================================
# 8. 이격도 계산 (멀티스레딩용)
# ==========================================
def fetch_disparity(row):
    code, name, market = row['Code'], row['Name'], row['Market']
    try:
        df = fdr.DataReader(code, start_date)
        if len(df) < 20:
            return None
        if sum(df['Volume'].tolist()[-20:]) / 20 < 100000:
            return None
        closes = df['Close'].tolist()
        ma20 = sum(closes[-20:]) / 20
        if ma20 == 0:
            return None
        disparity = round((closes[-1] / ma20) * 100, 2)
        return {'name': name, 'code': code, 'market': market, 'disparity': disparity}
    except:
        return None

# ==========================================
# 9. 지수 이격도
# ==========================================
def get_index_disparity():
    print("📈 코스피/코스닥 지수 이격도 계산 중...")
    result = {}
    idx_start = (CURRENT_KST - timedelta(days=60)).strftime("%Y-%m-%d")
    for code, name in [("^KS11", "KOSPI"), ("^KQ11", "KOSDAQ")]:
        try:
            df = fdr.DataReader(code, idx_start).dropna(subset=['Close'])
            df = df[~df.index.duplicated(keep='last')]
            if len(df) < 20:
                result[name] = None
                continue
            closes = df['Close'].tolist()
            disparity = round((closes[-1] / (sum(closes[-20:]) / 20)) * 100, 2)
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
# 10. 메인 로직
# ==========================================
def main():
    print(f"[{TARGET_DATE}] 프로그램 시작 (한국 시간 기준)")
    print(f"📅 DART 조회 기준연도: {BSNS_YEAR}")

    if is_holiday():
        msg = f"⏹️ [{TARGET_DATE}] 오늘은 휴장일입니다."
        print(msg)
        send_discord_message(msg)
        return

    print("✅ 분석을 시작합니다...")

    try:
        df_list = get_stock_list()
        if df_list.empty:
            raise Exception("종목 리스트가 비어있습니다.")

        krx_exclude = get_krx_filter()
        before = len(df_list)
        df_list = df_list[~df_list['Code'].isin(krx_exclude)]
        print(f"✅ KRX 필터 후: {before}개 → {len(df_list)}개")

        corp_map = get_corp_code_map()

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

        results = [r for r in all_analyzed if r['disparity'] <= 90.0]
        filter_level = "이격도 90% 이하"

        if not results:
            print("💡 90% 이하가 없어 95%로 범위를 넓힙니다.")
            results = [r for r in all_analyzed if r['disparity'] <= 95.0]
            filter_level = "이격도 95% 이하"

        print(f"📊 DART 재무정보 조회 중... ({len(results)}개 종목)")
        final_results = []
        excluded_nodata = 0

        for r in results:
            corp_code = corp_map.get(r['code'])
            if not corp_code:
                excluded_nodata += 1
                print(f"  ⚠️ 데이터없음 제외: {r['name']}({r['code']})")
                continue

            operating_income = get_dart_info(corp_code)

            if operating_income is None:
                excluded_nodata += 1
                print(f"  ⚠️ 데이터없음 제외: {r['name']}({r['code']})")
            else:
                r['operating_income'] = operating_income
                final_results.append(r)
            time.sleep(0.2)

        # 영업이익 높은순 정렬, 상위 50개
        final_results = sorted(final_results, key=lambda x: x.get('operating_income') or 0, reverse=True)[:50]

        print(f"✅ 데이터없음 제외: {excluded_nodata}개, 최종: {len(final_results)}개")

        capital_info = get_market_capital_info()
        index_disparity = get_index_disparity()

        if final_results:
            # 📨 메시지 1: 시장 이격도 + 자금현황
            msg1  = f"📈 **[{TARGET_DATE} 시장 이격도]**\n"
            msg1 += get_index_comment("KOSPI",  index_disparity.get('KOSPI'))  + "\n"
            msg1 += get_index_comment("KOSDAQ", index_disparity.get('KOSDAQ')) + "\n"
            msg1 += "\n" + "="*30 + "\n"
            msg1 += "💰 **[시장 자금 현황]**\n"
            msg1 += get_capital_comment(capital_info)
            send_discord_message(msg1)
            time.sleep(1)

            # 📨 메시지 2: 종목 분석 결과 + 체크리스트
            msg2  = f"📊 **[종목 분석 결과]** ({filter_level} / {BSNS_YEAR}년 기준 / 영업이익 높은순 상위 {len(final_results)}개)\n"
            msg2 += "="*30 + "\n"
            for r in final_results:
                oi = r.get('operating_income')
                oi_str = f"{oi/1e8:.0f}억" if oi is not None else "-"
                msg2 += f"· {r['name']} : {r['disparity']}% / {oi_str}\n"
            msg2 += "\n" + "="*30 + "\n"
            msg2 += "📝 **[Check List]**\n"
            msg2 += "1. 최근 일주일간 수급이 몰리는 테마순위로 표분류\n"
            msg2 += "2. 최근 일주일간 뉴스검색해서 주도테마 선정\n"
            msg2 += "3. 주도테마 고려해서 최대실적이 예상되거나 영업이익 전망이 좋은 기업순으로 추천\n"
            msg2 += "4. 추천한 종목들 이격도 하락 원인 분석해서 추천한게 맞는지 검증\n"
            send_discord_message(msg2)

            print(f"✅ 메시지 2개 전송 완료. (종목 {len(final_results)}개)")
        else:
            send_discord_message("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        err_msg = f"❌ 프로그램 오류: {e}"
        print(err_msg)
        send_discord_message(err_msg)

if __name__ == "__main__":
    main()
