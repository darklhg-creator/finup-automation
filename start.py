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

# [한국 시간 설정]
KST_TIMEZONE = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST_TIMEZONE)
TARGET_DATE = CURRENT_KST.strftime("%Y-%m-%d")

# ==========================================
# 1. 공통 함수
# ==========================================
def send_discord_message(content):
    """디스코드 메시지 전송 함수"""
    try:
        if len(content) <= 2000:
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': content})
        else:
            for i in range(0, len(content), 2000):
                requests.post(IGYEOK_WEBHOOK_URL, json={'content': content[i:i+2000]})
                time.sleep(0.5)
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

def get_market_indices():
    """야후 파이낸스 소스로 지수 이격도 계산"""
    try:
        # 코스피(^KS11), 코스닥(^KQ11)
        kospi = fdr.DataReader('^KS11', start='2024-01-01')
        kosdaq = fdr.DataReader('^KQ11', start='2024-01-01')
        
        def calc_disp(df):
            if df.empty or len(df) < 20: return 0, 0, 0
            curr = df['Close'].iloc[-1]
            # 일간(20일), 주간(20주), 월간(20월) 이격도 계산
            d = round((curr / df['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
            w = round((curr / df.resample('W').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
            m = round((curr / df.resample('ME').last()['Close'].rolling(20).mean().iloc[-1]) * 100, 1)
            return d, w, m
        
        return calc_disp(kospi), calc_disp(kosdaq)
    except:
        return (0,0,0), (0,0,0)

# ==========================================
# 2. 메인 로직
# ==========================================
def main():
    print(f"[{TARGET_DATE}] 프로그램 시작 (한국 시간 기준)")

    # [1] 휴장일 체크
    weekday = CURRENT_KST.weekday()
    if weekday >= 5:
        day_name = "토요일" if weekday == 5 else "일요일"
        msg = f"⏹️ 오늘은 주말({day_name})이라 주식장이 열리지 않습니다."
        print(msg)
        send_discord_message(msg)
        return

    try:
        check_market = fdr.DataReader('KS11', TARGET_DATE, TARGET_DATE)
        if check_market.empty:
            msg = f"⏹️ 오늘은 공휴일(장 휴무)이라 주식장이 열리지 않습니다."
            print(msg)
            send_discord_message(msg)
            return
    except:
        print("⚠️ 장 운영 여부 확인 중 오류 발생 (진행함)")

    # [2] 시장 지수 정보 수집
    kp, kq = get_market_indices()

    # [3] 종목 리스트 확보 (KRX)
    print("📡 KRX 종목 리스트 수집 중...")
    df_krx = fdr.StockListing('KRX')
    # 분석 대상 (KOSPI, KOSDAQ 상위 종목 중심)
    stocks = df_krx[df_krx['Market'].isin(['KOSPI', 'KOSDAQ'])].head(1200)

    # [4] 개별 종목 분석
    all_analyzed = []
    print(f"🚀 [1단계] 이격도 분석 시작 (대상: {len(stocks)}개 종목)")

    for _, row in stocks.iterrows():
        try:
            code, name = row['Code'], row['Name']
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue

            current_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            
            if ma20 == 0 or pd.isna(ma20): continue
            
            disparity = round((current_price / ma20) * 100, 1)
            credit = row.get('MarginRate', 0) # 신용비율 데이터가 있을 경우

            all_analyzed.append({
                'name': name, 
                'code': code, 
                'disparity': disparity,
                'credit': credit
            })
        except:
            continue

    # [5] 계단식 필터링
    results = [r for r in all_analyzed if r['disparity'] <= 90.0]
    filter_level = "이격도 90% 이하 (초과대낙폭)"

    if len(results) < 10:
        results = [r for r in all_analyzed if r['disparity'] <= 95.0]
        filter_level = "이격도 95% 이하 (일반낙폭)"

    # [6] 리포트 생성 및 전송
    if results:
        results = sorted(results, key=lambda x: x['disparity'])
        
        report = f"### 🌍 KRX 시장 현황 ({TARGET_DATE})\n"
        report += f"**[코스피 이격]** 일:{kp[0]}% / 주:{kp[1]}% / 월:{kp[2]}%\n"
        report += f"**[코스닥 이격]** 일:{kq[0]}% / 주:{kq[1]}% / 월:{kq[2]}%\n\n"
        report += f"### 🎯 분석 결과 ({filter_level})\n"
        
        for r in results[:40]:
            risk = "안전" if r['credit'] < 5 else "주의"
            report += f"· **{r['name']}({r['code']})**: {r['disparity']}% (신용 {r['credit']}%, {risk})\n"

        # 체크리스트 추가
        report += "\n" + "="*30 + "\n"
        report += "📝 **[Check List]**\n"
        report += "1. 영업이익 적자기업 제외하고 테마별로 표로 분류\n"
        report += "2. 기관/외국인/연기금 수급 분석\n"
        report += "3. 최근 일주일 뉴스 및 목표주가 검색\n"
        report += "4. 테마/수급/영업이익 전망 종합 최종 선정\n"

        send_discord_message(report)
        
        # targets.txt 저장
        with open("targets.txt", "w", encoding="utf-8") as f:
            lines = [f"{r['code']},{r['name']}" for r in results]
            f.write("\n".join(lines))
        
        print(f"✅ 분석 완료 및 리포트 전송 완료 (추출된 종목: {len(results)}개)")
    else:
        msg = "🔍 조건에 해당되는 종목이 없습니다."
        print(msg)
        send_discord_message(msg)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        err_msg = f"❌ 시스템 오류 발생: {e}"
        print(err_msg)
        send_discord_message(err_msg)
