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
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

KST_TIMEZONE = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST_TIMEZONE)
TARGET_DATE = CURRENT_KST.strftime("%Y-%m-%d")

# ==========================================
# 1. 공통 함수
# ==========================================
def send_discord_message(content):
    try:
        if len(content) <= 2000:
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': content})
        else:
            for i in range(0, len(content), 2000):
                requests.post(IGYEOK_WEBHOOK_URL, json={'content': content[i:i+2000]})
                time.sleep(0.5)
    except Exception as e:
        print(f"전송 실패: {e}")

def get_naver_credit_ratio(code):
    """개별 종목 신용비율 크롤링"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        for th in soup.find_all('th'):
            if '신용비율' in th.get_text():
                td = th.find_next('td')
                val = td.get_text().replace('%','').replace(',','').strip()
                return float(val)
        return 0.0
    except: return 0.0

def get_market_fund_info():
    """시장 지표 (예탁금, 신용잔고) 크롤링"""
    try:
        url = "https://finance.naver.com/sise/sise_deposit.naver"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 예탁금
        dep_row = soup.select_one('div#type_1 table.type_2 tr:nth-child(2) td:nth-child(2)')
        dep_val = round(int(dep_row.get_text().replace(',','').strip()) / 1000000, 2) if dep_row else 0
        
        # 신용잔고 분리
        rows = soup.select('div#type_0 table.type_2 tr')
        ksp_c, ksd_c = 0.0, 0.0
        for r in rows:
            tds = r.select('td')
            if '유가증권' in r.text and len(tds) > 0:
                ksp_c = round(int(tds[0].text.replace(',','').strip()) / 1000000, 2)
            elif '코스닥' in r.text and len(tds) > 0:
                ksd_c = round(int(tds[0].text.replace(',','').strip()) / 1000000, 2)
        return dep_val, ksp_c, ksd_c
    except: return 0, 0, 0

def get_market_disparity(ticker):
    """지수 이격도 계산"""
    try:
        df = fdr.DataReader(ticker, start='2024-01-01')
        curr = df['Close'].iloc[-1]
        d = round((curr / df['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
        w = round((curr / df.resample('W').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
        m = round((curr / df.resample('ME').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
        return d, w, m
    except: return 0, 0, 0

def main():
    print(f"[{TARGET_DATE}] 계단식 이격도 분석 시작...")
    
    # 1. 지표 수집
    dep, ksp_c, ksd_c = get_market_fund_info()
    kp_d, kp_w, kp_m = get_market_disparity('KS11')
    kq_d, kq_w, kq_m = get_market_disparity('KQ11')
    
    # 2. 전 종목 스캔 (KOSPI 500 + KOSDAQ 1000)
    stocks = pd.concat([fdr.StockListing('KOSPI').head(500), fdr.StockListing('KOSDAQ').head(1000)])
    all_analyzed = []
    
    for _, row in stocks.iterrows():
        try:
            df = fdr.DataReader(row['Code']).tail(30)
            if len(df) < 20: continue
            curr = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            disp = round((curr / ma20) * 100, 1)
            all_analyzed.append({'c': row['Code'], 'n': row['Name'], 'd': disp})
        except: continue

    # 3. 계단식 필터링 (90% 이하 먼저, 10개 미만이면 95%로 확대)
    results = [r for r in all_analyzed if r['d'] <= 90.0]
    filter_msg = "이격도 90% 이하 (초과대낙폭)"
    
    if len(results) < 10:
        results = [r for r in all_analyzed if r['d'] <= 95.0]
        filter_msg = "이격도 95% 이하 (일반낙폭)"

    # 4. 리포트 생성
    report = f"### 🌍 시장 지표 브리핑 ({TARGET_DATE})\n"
    report += f"**[자금]** 예탁금: {dep}조 / **[신용]** 코스피: {ksp_c}조, 코스닥: {ksd_c}조\n"
    report += f"**[코스피 이격]** 일:{kp_d}% / 주:{kp_w}% / 월:{kp_m}%\n"
    report += f"**[코스닥 이격]** 일:{kq_d}% / 주:{kq_w}% / 월:{kq_m}%\n\n"
    report += f"### 🎯 종목 분석 결과 ({filter_msg})\n"
    
    if results:
        for r in sorted(results, key=lambda x: x['d'])[:50]:
            cr = get_naver_credit_ratio(r['c'])
            risk = "안전" if cr < 5 else ("⚠️주의" if cr < 7 else "🚫위험")
            report += f"· **{r['n']}({r['c']})**: {r['d']}% (신용 {cr}%, {risk})\n"
            time.sleep(0.05)
    else:
        report += "🔍 조건에 맞는 종목이 없습니다.\n"
        
    report += "\n" + "="*25 + "\n"
    report += "📝 **[Check List]**\n1. 영업이익 적자기업 제외하고 테마별로 표로 분류\n2. 1번에서 정리한 기업들 오늘 장마감 기준 기관/외국인/연기금 수급 분석\n3. 2번 기업들 최근 일주일 뉴스 및 목표주가 검색\n4. 테마/수급/영업이익 전망 종합하여 최종 종목 선정"
    
    send_discord_message(report)
    print("✅ 리포트 전송 완료")

if __name__ == "__main__":
    main()
