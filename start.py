import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import sys
import time

# ==========================================
# 0. 사용자 설정
# ==========================================
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

KST_TIMEZONE = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST_TIMEZONE)
TARGET_DATE = CURRENT_KST.strftime("%Y-%m-%d")

# ==========================================
# 1. 핵심 로직: KRX 및 야후 데이터 활용
# ==========================================
def send_discord_message(content):
    try:
        if len(content) <= 2000:
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': content})
        else:
            for i in range(0, len(content), 2000):
                requests.post(IGYEOK_WEBHOOK_URL, json={'content': content[i:i+2000]})
                time.sleep(0.5)
    except: pass

def get_market_indices():
    """야후 파이낸스 소스로 지수 이격도 계산 (네이버 차단 우회)"""
    try:
        # 코스피(^KS11), 코스닥(^KQ11)
        kospi = fdr.DataReader('^KS11', start='2024-01-01')
        kosdaq = fdr.DataReader('^KQ11', start='2024-01-01')
        
        def calc_disp(df):
            if df.empty: return 0, 0, 0
            curr = df['Close'].iloc[-1]
            d = round((curr / df['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
            w = round((curr / df.resample('W').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
            m = round((curr / df.resample('ME').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
            return d, w, m
        
        return calc_disp(kospi), calc_disp(kosdaq)
    except:
        return (0,0,0), (0,0,0)

def main():
    print(f"[{TARGET_DATE}] KRX 기반 분석 시작...")
    
    # 1. 시장 지수 정보 (야후 소스)
    kp, kq = get_market_indices()
    
    # 2. KRX 전체 종목 리스트 확보 (공식 소스)
    print("📡 KRX 종목 리스트 수집 중...")
    df_krx = fdr.StockListing('KRX') # 네이버 대신 KRX 공식 리스트
    
    # 분석 대상 축소 (상위 종목 위주로 속도 향상)
    stocks = df_krx[df_krx['Market'].isin(['KOSPI', 'KOSDAQ'])].head(1200)
    
    all_analyzed = []
    for _, row in stocks.iterrows():
        try:
            code, name = row['Code'], row['Name']
            # 주가 데이터 수집
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            curr = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            disp = round((curr / ma20) * 100, 1)
            
            # 신용비율 정보가 StockListing에 포함되어 있는지 확인 (일부 환경)
            # 없으면 기존 크롤링 방식을 쓰되, 차단 방지를 위해 딜레이 강화
            credit = row.get('MarginRate', 0) # KRX 데이터에 포함된 경우 활용
            
            all_analyzed.append({'c': code, 'n': name, 'd': disp, 'cr': credit})
        except: continue

    # 3. 계단식 필터링 로직
    results = [r for r in all_analyzed if r['d'] <= 90.0]
    filter_msg = "90% 이하 (초과대낙폭)"
    if len(results) < 10:
        results = [r for r in all_analyzed if r['d'] <= 95.0]
        filter_msg = "95% 이하 (일반낙폭)"

    # 4. 리포트 생성
    report = f"### 🌍 KRX 시장 현황 ({TARGET_DATE})\n"
    report += f"**[코스피 이격]** 일:{kp[0]}% / 주:{kp[1]}% / 월:{kp[2]}%\n"
    report += f"**[코스닥 이격]** 일:{kq[0]}% / 주:{kq[1]}% / 월:{kq[2]}%\n\n"
    
    report += f"### 🎯 분석 결과 ({filter_msg})\n"
    
    for r in sorted(results, key=lambda x: x['d'])[:40]:
        risk = "안전" if r['cr'] < 5 else "주의"
        # 신용 데이터가 KRX 리스트에 없을 경우 0으로 표기되는 한계는 있음
        report += f"· **{r['n']}({r['c']})**: {r['d']}% (신용 {r['cr']}%, {risk})\n"

    send_discord_message(report)
    print("✅ 분석 리포트 전송 완료")

if __name__ == "__main__":
    main()
