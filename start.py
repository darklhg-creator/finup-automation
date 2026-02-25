import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import sys

# ==========================================
# 0. 사용자 설정
# ==========================================
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

# [한국 시간 설정] - 서버 시간이 달라도 한국 시간으로 고정
KST_TIMEZONE = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST_TIMEZONE)
TARGET_DATE = CURRENT_KST.strftime("%Y-%m-%d") # FDR은 YYYY-MM-DD 포맷 권장

# ==========================================
# 1. 공통 함수
# ==========================================
def send_discord_message(content):
    """디스코드 메시지 전송 함수"""
    try:
        data = {'content': content}
        requests.post(IGYEOK_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

# ==========================================
# 2. 메인 로직
# ==========================================
def main():
    print(f"[{TARGET_DATE}] 프로그램 시작 (한국 시간 기준)")

    # ---------------------------------------------------------
    # [휴장일 체크 로직 추가]
    # ---------------------------------------------------------
    
    # 1. 주말 체크 (월:0 ~ 일:6)
    weekday = CURRENT_KST.weekday()
    if weekday >= 5:
        day_name = "토요일" if weekday == 5 else "일요일"
        msg = f"⏹️ 오늘은 주말({day_name})이라 주식장이 열리지 않습니다."
        print(msg)
        send_discord_message(msg)
        sys.exit() # 프로그램 종료

    # 2. 공휴일 체크 (KOSPI 지수 데이터로 개장 여부 확인)
    # 오늘 날짜의 KOSPI(KS11) 데이터가 없으면 휴장일로 간주
    try:
        check_market = fdr.DataReader('KS11', TARGET_DATE, TARGET_DATE)
        if check_market.empty:
            msg = f"⏹️ 오늘은 공휴일(장 휴무)이라 주식장이 열리지 않습니다."
            print(msg)
            send_discord_message(msg)
            sys.exit() # 프로그램 종료
    except Exception as e:
        msg = f"⚠️ 장 운영 여부 확인 실패 ({e}). 프로그램을 종료합니다."
        print(msg)
        send_discord_message(msg)
        sys.exit()
    
    print(f"✅ 정상 개장일입니다. 분석을 시작합니다...")
    
    # ---------------------------------------------------------
    # [기존 분석 로직 시작]
    # ---------------------------------------------------------
    print("🚀 [1단계] 계단식 이격도 분석 시작 (KOSPI 500 + KOSDAQ 1000)")
    
    try:
        # 1. 대상 종목 리스트 확보
        df_kospi = fdr.StockListing('KOSPI').head(500)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(1000)
        df_total = pd.concat([df_kospi, df_kosdaq])
        
        all_analyzed = []
        print(f"📡 총 {len(df_total)}개 종목 데이터 수집 중...")

        for idx, row in df_total.iterrows():
            code = row['Code']
            name = row['Name']
            try:
                df = fdr.DataReader(code).tail(30)
                if len(df) < 20: continue
                
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                
                if ma20 == 0 or pd.isna(ma20): continue
                    
                disparity = round((current_price / ma20) * 100, 1)
                all_analyzed.append({'name': name, 'code': code, 'disparity': disparity})
            except:
                continue

        # 2. 계단식 필터링 로직
        results = [r for r in all_analyzed if r['disparity'] <= 90.0]
        filter_level = "이격도 90% 이하 (초과대낙폭)"

        if not results:
            print("💡 이격도 90% 이하 종목이 없어 범위를 95%로 확대합니다.")
            results = [r for r in all_analyzed if r['disparity'] <= 95.0]
            filter_level = "이격도 95% 이하 (일반낙폭)"

        # 3. 결과 처리 및 전송
        if results:
            results = sorted(results, key=lambda x: x['disparity'])
            
            # 리포트 제목 및 본문 구성
            report = f"### 📊 종목 분석 결과 ({filter_level})\n"
            for r in results[:50]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}%\n"
            
            # --- 요청하신 체크리스트 문구 추가 ---
            report += "\n" + "="*30 + "\n"
            report += "📝 **[Check List]**\n"
            report += "1. 영업이익 적자기업 제외하고 테마별로 표로 분류\n"
            report += "2. 1번에서 정리한 기업들 최근 일주일간 뉴스확인, 언제 뉴스인지 날자도 같이 정리 \n"
            report += "3. 2번 기업들 목표주가 검색\n"
            report += "4. 테마/수급/영업이익 전망 종합하여 최종 종목 선정\n"
            # -----------------------------------
            
            # 디스코드 전송
            send_discord_message(report)
            
            # 차례대로 targets.txt 저장
            with open("targets.txt", "w", encoding="utf-8") as f:
                lines = [f"{r['code']},{r['name']}" for r in results]
                f.write("\n".join(lines))
            
            print(f"✅ {filter_level} 조건으로 {len(results)}개 추출 완료.")
        else:
            msg = "🔍 95% 이하 조건에도 해당되는 종목이 없습니다."
            print(msg)
            send_discord_message(msg)

    except Exception as e:
        err_msg = f"❌ 에러 발생: {e}"
        print(err_msg)
        send_discord_message(err_msg)

if __name__ == "__main__":
    main()
