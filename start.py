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

KST_TIMEZONE = timezone(timedelta(hours=9))
CURRENT_KST = datetime.now(KST_TIMEZONE)
TARGET_DATE = CURRENT_KST.strftime("%Y-%m-%d")

# ==========================================
# 1. 공통 함수
# ==========================================
def send_discord_message(content):
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

    # 1. 주말 체크
    weekday = CURRENT_KST.weekday()
    if weekday >= 5:
        msg = "⏹️ 오늘은 주말이라 주식장이 열리지 않습니다."
        print(msg)
        send_discord_message(msg)
        return

    print(f"✅ 분석을 시작합니다...")

    try:
        # [수정 포인트] 서버 에러를 피하기 위해 주요 종목 리스트를 직접 정의합니다.
        # 우선 테스트를 위해 주요 대형주 10개를 넣었습니다. 
        # 나중에 분석하고 싶은 종목 코드를 'codes' 리스트에 추가하시면 됩니다.
        print("📡 서버 점검 우회: 주요 종목 분석 모드로 전환합니다...")
        
        target_stocks = [
            {'Code': '005930', 'Name': '삼성전자'},
            {'Code': '000660', 'Name': 'SK하이닉스'},
            {'Code': '373220', 'Name': 'LG에너지솔루션'},
            {'Code': '207940', 'Name': '삼성바이오로직스'},
            {'Code': '005380', 'Name': '현대차'},
            {'Code': '005490', 'Name': 'POSCO홀딩스'},
            {'Code': '000270', 'Name': '기아'},
            {'Code': '035420', 'Name': 'NAVER'},
            {'Code': '006400', 'Name': '삼성SDI'},
            {'Code': '068270', 'Name': '셀트리온'}
        ]
        
        df_total = pd.DataFrame(target_stocks)

        all_analyzed = []
        print(f"📡 총 {len(df_total)}개 종목 분석 중...")

        for idx, row in df_total.iterrows():
            code = row['Code']
            name = row['Name']
            
            try:
                # 개별 주가 데이터(DataReader)는 보통 잘 작동합니다.
                df = fdr.DataReader(code)
                if df is None or len(df) < 20:
                    continue
                
                df = df.tail(30)
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]

                if pd.isna(ma20) or ma20 == 0:
                    continue

                disparity = round((current_price / ma20) * 100, 1)
                all_analyzed.append({'name': name, 'code': code, 'disparity': disparity})
            except:
                continue

        # 2. 필터링 로직 (조건 완화: 테스트를 위해 100% 이하로 설정)
        results = [r for r in all_analyzed if r['disparity'] <= 100.0]
        filter_level = "이격도 100% 이하 (분석 대상)"

        # 3. 결과 전송
        if results:
            results = sorted(results, key=lambda x: x['disparity'])
            report = f"### 📊 종목 분석 결과 ({filter_level})\n"
            for r in results[:30]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}%\n"

            report += "\n" + "="*30 + "\n"
            report += "📝 **[Check List]**\n1. 적자기업 제외/테마 분류\n2. 최근 뉴스 확인\n3. 하락 원인 분석\n4. 최종 선정"
            
            send_discord_message(report)
            print(f"✅ 분석 완료! {len(results)}개 추출됨.")
        else:
            print("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        err_msg = f"❌ 메인 로직 에러 발생: {e}"
        print(err_msg)
        send_discord_message(err_msg)

if __name__ == "__main__":
    main()
