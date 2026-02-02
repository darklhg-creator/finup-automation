import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import sys
from bs4 import BeautifulSoup  # [추가] 웹 크롤링용 라이브러리
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
        data = {'content': content}
        requests.post(IGYEOK_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

def get_naver_credit_ratio(code):
    """
    [추가] 네이버 금융에서 해당 종목의 신용비율(%)을 크롤링하는 함수
    """
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 네이버 금융 페이지 구조상 '신용비율' 텍스트가 있는 곳을 찾음
        # 보통 table.no_info 내부에 있음
        rows = soup.select('table.no_info tr')
        for row in rows:
            if '신용비율' in row.text:
                data = row.select_one('td em')
                if data:
                    return float(data.text.strip().replace('%', ''))
        return 0.0 # 못 찾으면 0.0 반환
    except:
        return 0.0 # 에러 시 0.0 반환

# ==========================================
# 2. 메인 로직
# ==========================================
def main():
    print(f"[{TARGET_DATE}] 프로그램 시작 (한국 시간 기준)")

    # ---------------------------------------------------------
    # [휴장일 체크 로직]
    # ---------------------------------------------------------
    weekday = CURRENT_KST.weekday()
    if weekday >= 5:
        day_name = "토요일" if weekday == 5 else "일요일"
        msg = f"⏹️ 오늘은 주말({day_name})이라 주식장이 열리지 않습니다."
        print(msg)
        send_discord_message(msg)
        sys.exit()

    try:
        check_market = fdr.DataReader('KS11', TARGET_DATE, TARGET_DATE)
        if check_market.empty:
            msg = f"⏹️ 오늘은 공휴일(장 휴무)이라 주식장이 열리지 않습니다."
            print(msg)
            send_discord_message(msg)
            sys.exit()
    except Exception as e:
        msg = f"⚠️ 장 운영 여부 확인 실패 ({e}). 프로그램을 종료합니다."
        print(msg)
        send_discord_message(msg)
        sys.exit()
    
    print(f"✅ 정상 개장일입니다. 분석을 시작합니다...")
    
    # ---------------------------------------------------------
    # [분석 로직 시작]
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

        # 3. [추가] 선별된 종목들에 대해 신용비율 크롤링
        if results:
            print(f"🔍 선별된 {len(results)}개 종목의 신용비율을 조회합니다...")
            
            # 이격도 낮은 순 정렬
            results = sorted(results, key=lambda x: x['disparity'])
            
            # 리포트 제목 구성
            report = f"### 📊 종목 분석 결과 ({filter_level})\n"
            
            # 결과 루프 돌면서 신용비율 확인 및 메시지 작성
            for r in results[:50]:
                # 신용비율 조회 (속도 조절을 위해 약간의 딜레이가 생길 수 있음)
                credit_ratio = get_naver_credit_ratio(r['code'])
                
                # 리스크 라벨링
                risk_label = "안전"
                if credit_ratio >= 7.0:
                    risk_label = "🚫매우위험"
                elif credit_ratio >= 5.0:
                    risk_label = "⚠️주의"
                
                # [요청하신 포맷 적용]
                # 예: 아우토크립트(331740): 89.5%(신용잔고 5.2%, ⚠️주의)
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}% (신용 {credit_ratio}%, {risk_label})\n"
                
                # 차단 방지용 미세 딜레이
                time.sleep(0.05) 
            
            # --- 요청하신 체크리스트 문구 ---
            report += "\n" + "="*30 + "\n"
            report += "📝 **[Check List]**\n"
            report += "1. 영업이익 적자기업 제외하고 테마별로 표로 분류\n"
            report += "2. 1번에서 정리한 기업들 오늘 장마감 기준 기관/외국인/연기금 수급 분석\n"
            report += "3. 2번 기업들 최근 일주일 뉴스 및 목표주가 검색\n"
            report += "4. 테마/수급/영업이익 전망 종합하여 최종 종목 선정\n"
            # -----------------------------------
            
            # 디스코드 전송
            send_discord_message(report)
            
            # targets.txt 저장
            with open("targets.txt", "w", encoding="utf-8") as f:
                lines = [f"{r['code']},{r['name']}" for r in results]
                f.write("\n".join(lines))
            
            print(f"✅ {filter_level} 조건으로 {len(results)}개 추출 및 전송 완료.")
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
