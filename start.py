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
IGYEOK_WEBHOOK_URL = os.environ.get("IGYEOK_WEBHOOK_URL")

KST_TIMEZONE = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST_TIMEZONE)
TARGET_DATE = CURRENT_KST.strftime("%Y-%m-%d")

def send_discord_message(content):
    if not IGYEOK_WEBHOOK_URL: return
    try:
        # 메시지가 너무 길면 디스코드에서 잘리므로 분할 전송 처리가 필요할 수 있음
        data = {'content': content}
        requests.post(IGYEOK_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

def get_naver_credit_ratio(code):
    """개별 종목 신용비율 정밀 크롤링"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # '신용비율' 텍스트를 포함한 th 탐색
        for th in soup.find_all('th'):
            if '신용비율' in th.get_text():
                td = th.find_next('td')
                val = td.get_text().replace('%','').replace(',','').strip()
                return float(val) if val else 0.0
        return 0.0
    except: return 0.0

def get_market_fund_info():
    """시장별 신용잔고 분리 크롤링"""
    try:
        url = "https://finance.naver.com/sise/sise_deposit.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 예탁금
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
    except: return 0, 0, 0

def get_market_disparity(ticker):
    """지수 이격도 (일/주/월)"""
    try:
        df = fdr.DataReader(ticker, start=(CURRENT_KST - timedelta(days=730)).strftime('%Y-%m-%d'))
        curr = df['Close'].iloc[-1]
        d = round((curr / df['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
        w = round((curr / df.resample('W').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
        m = round((curr / df.resample('M').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
        return d, w, m
    except: return 0, 0, 0

def main():
    # 1. 시장 지표
    dep, ksp_c, ksd_c = get_market_fund_info()
    kp_d, kp_w, kp_m = get_market_disparity('KS11')
    kq_d, kq_w, kq_m = get_market_disparity('KQ11')
    
    # 2. 종목 스캔
    stocks = pd.concat([fdr.StockListing('KOSPI').head(400), fdr.StockListing('KOSDAQ').head(800)])
    found = []
    for _, row in stocks.iterrows():
        try:
            df = fdr.DataReader(row['Code']).tail(30)
            if len(df) < 20: continue
            disp = round((df['Close'].iloc[-1] / df['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
            if disp <= 95.0:
                found.append({'c': row['Code'], 'n': row['Name'], 'd': disp})
        except: continue

    # 3. 리포트
    report = f"### 🌍 시장 지표 ({TARGET_DATE})\n"
    report += f"**[자금]** 예탁금: {dep}조\n"
    report += f"**[신용]** 코스피: {ksp_c}조 / 코스닥: {ksd_c}조\n"
    report += f"**[코스피 이격]** 일:{kp_d}% / 주:{kp_w}% / 월:{kp_m}%\n"
    report += f"**[코스닥 이격]** 일:{kq_d}% / 주:{kq_w}% / 월:{kq_m}%\n\n"
    
    report += "### 🎯 종목 발굴 (이격도 95% 이하)\n"
    for r in sorted(found, key=lambda x: x['d'])[:40]:
        c_ratio = get_naver_credit_ratio(r['c'])
        risk = "안전" if c_ratio < 5 else ("⚠️주의" if c_ratio < 7 else "🚫위험")
        report += f"· **{r['n']}({r['c']})**: {r['d']}% (신용 {c_ratio}%, {risk})\n"
        time.sleep(0.1) # 크롤링 차단 방지

    send_discord_message(report)

if __name__ == "__main__":
    main()
