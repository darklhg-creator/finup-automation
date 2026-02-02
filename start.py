import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import sys
from bs4 import BeautifulSoup
import time

# ==========================================
# 0. 사용자 설정
# ==========================================
# 깃허브 세팅 문제 방지를 위해 URL을 직접 입력합니다.
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

KST_TIMEZONE = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST_TIMEZONE)
TARGET_DATE = CURRENT_KST.strftime("%Y-%m-%d")

# ==========================================
# 1. 공통 함수
# ==========================================
def send_discord_message(content):
    """디스코드 메시지 전송 (2000자 초과 시 분할 전송)"""
    try:
        if len(content) <= 2000:
            data = {'content': content}
            requests.post(IGYEOK_WEBHOOK_URL, json=data)
        else:
            # 2000자씩 끊어서 전송
            for i in range(0, len(content), 2000):
                part = content[i:i+2000]
                requests.post(IGYEOK_WEBHOOK_URL, json={'content': part})
                time.sleep(0.5)
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

def get_naver_credit_ratio(code):
    """개별 종목 신용비율 정밀 크롤링 (0.0% 방지)"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # '신용비율' 텍스트를 포함한 th 탐색
        for th in soup.find_all('th'):
            if '신용비율' in th.get_text():
                td = th.find_next('td')
                val_text = td.get_text().replace('%','').replace(',','').strip()
                return float(val_text)
        return 0.0
    except:
        return 0.0

def get_market_fund_info():
    """시장별 신용잔고 분리 크롤링 (코스피/코스닥)"""
    try:
        url = "https://finance.naver.com/sise/sise_deposit.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 고객예탁금
        dep = soup.select_one('div#type_1 table.type_2 tr:nth-child(2) td:nth-child(2)').text
        dep_val = round(int(dep.replace(',','')) / 1000000, 2)
        
        # 신용잔고 (코스피/코스닥 분리)
        rows = soup.select('div#type_0 table.type_2 tr')
        ksp_c, ksd_c = 0.0, 0.0
        for r in rows:
            if '유가증권' in r.text:
                ksp_c = round(int(r.select('td')[0].text.replace(',','')) / 1000000, 2)
            elif '코스닥' in r.text:
                ksd_c = round(int(r.select('td')[0].text.replace(',','')) / 1000000, 2)
        return dep_val, ksp_c, ksd_c
    except:
        return 0, 0, 0

def get_market_disparity(ticker):
    """지수 이격도 계산 (일/주/월)"""
    try:
        df = fdr.DataReader(ticker, start=(CURRENT_KST - timedelta(days=730)).strftime('%Y-%m-%d'))
        curr = df['Close'].iloc[-1]
        
        # 일봉(20), 주봉(20), 월봉(20)
        d = round((curr / df['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
        w = round((curr / df.resample('W').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
        m = round((curr / df.resample('ME').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1) # M -> ME로 수정 (경고 방지)
        return d, w, m
    except:
        return 0, 0, 0

# ==========================================
# 2. 메인 로직
# ==========================================
def main():
    print(f"[{TARGET_DATE}] 분석 프로세스 시작...")

    # 1. 시장 지표 수집
    dep, ksp_c, ksd_c = get_market_fund_info()
    kp_d, kp_w, kp_m = get_market_disparity('KS11')
    kq_d, kq_w, kq_m = get_market_disparity('KQ11')
    
    # 2. 종목 스캔 (속도를 위해 KOSPI 200 + KOSDAQ 400으로 우선 축소)
    print("🚀 종목 스캔 중...")
    stocks_kospi = fdr.StockListing('KOSPI').head(200)
    stocks_kosdaq = fdr.StockListing('KOSDAQ').head(400)
    stocks = pd.concat([stocks_kospi, stocks_kosdaq])
    
    found = []
    for _, row in stocks.iterrows():
        try:
            code, name = row['Code'], row['Name']
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            curr_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            disp = round((curr_price / ma20) * 100, 1)
            
            if disp <= 95.0: # 이격도 95% 이하만 선별
                found.append({'c': code, 'n': name, 'd': disp})
        except:
            continue

    # 3. 리포트 본문 구성
    report = f"### 🌍 시장 지표 브리핑 ({TARGET_DATE})\n"
    report += f"**[자금]** 예탁금: {dep}조\n"
    report += f"**[신용]** 코스피: {ksp_c}조 / 코스닥: {ksd_c}조\n"
    report += f"**[코스피 이격]** 일:{kp_d}% / 주:{kp_w}% / 월:{kp_m}%\n"
    report += f"**[코스닥 이격]** 일:{kq_d}% / 주:{kq_w}% / 월:{kq_m}%\n\n"
    
    report += "### 🎯 이격도 과매도 종목 (95% 이하)\n"
    
    if found:
        # 이격도 낮은 순으로 정렬
        sorted_found = sorted(found, key=lambda x: x['d'])
        for r in sorted_found[:40]: # 상위 40개
            c_ratio = get_naver_credit_ratio(r['c'])
            risk = "안전" if c_ratio < 5 else ("⚠️주의" if c_ratio < 7 else "🚫위험")
            report += f"· **{r['n']}({r['c']})**: {r['d']}% (신용 {c_ratio}%, {risk})\n"
            time.sleep(0.1) # 네이버 차단 방지용 딜레이
    else:
        report += "🔍 해당 조건의 종목이 없습니다.\n"

    report += "\n" + "="*20 + "\n"
    report += "📝 **[Check List]**\n1. 영업이익 흑자 확인\n2. 기관/외국인 수급 체크"

    # 4. 전송
    send_discord_message(report)
    print("✅ 디스코드 전송 완료.")

if __name__ == "__main__":
    main()
