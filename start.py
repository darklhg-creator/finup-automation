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
        print("⏹️ 오늘은 주말이라 종료합니다.")
        return

    print(f"✅ 분석을 시작합니다...")

    try:
        # [고도화] 서버 에러 발생 시 여러 방법을 시도합니다.
        print("📡 종목 리스트 불러오는 중...")
        try:
            # 첫 번째 시도: KRX 통합
            df_total = fdr.StockListing('KRX')
        except:
            try:
                # 두 번째 시도: KOSPI + KOSDAQ 합치기
                df_kospi = fdr.StockListing('KOSPI')
                df_kosdaq = fdr.StockListing('KOSDAQ')
                df_total = pd.concat([df_kospi, df_kosdaq])
            except Exception as e:
                # 최후의 수단: 에러 발생 시 프로그램 종료 및 알림
                raise Exception(f"거래소 서버 응답 없음 (StockListing 실패): {e}")

        # 분석 대상 제한 (KOSPI 상위 500, KOSDAQ 상위 1000)
        df_kospi = df_total[df_total['Market'] == 'KOSPI'].head(500)
        df_kosdaq = df_total[df_total['Market'] == 'KOSDAQ'].head(1000)
        df_final_list = pd.concat([df_kospi, df_kosdaq])

        all_analyzed = []
        total_len = len(df_final_list)
        print(f"📡 총 {total_len}개 종목 분석 시작 (잠시만 기다려 주세요)...")

        for idx, row in df_final_list.iterrows():
            code = row['Code']
            name = row['Name']
            
            try:
                # 개별 종목 데이터는 안정적입니다.
                df = fdr.DataReader(code).tail(30)
                if len(df) < 20: continue
                
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]

                if pd.isna(ma20) or ma20 == 0: continue

                disparity = round((current_price / ma20) * 100, 1)
                all_analyzed.append({'name': name, 'code': code, 'disparity': disparity})
            except:
                continue

        # 2. 계단식 필터링 (다시 90% 기준으로 강화)
        results = [r for r in all_analyzed if r['disparity'] <= 90.0]
        filter_level = "이격도 90% 이하 (초과대낙폭)"

        if not results:
            print("💡 90% 이하가 없어 95%로 범위를 넓힙니다.")
            results = [r for r in all_analyzed if r['disparity'] <= 95.0]
            filter_level = "이격도 95% 이하 (일반낙폭)"

        # 3. 결과 처리 및 전송
        if results:
            results = sorted(results, key=lambda x: x['disparity'])
            
            report = f"### 📊 종목 분석 결과 ({filter_level})\n"
            # 너무 많으면 전송이 안 되므로 상위 40개만
            for r in results[:40]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}%\n"

            report += "\n" + "="*30 + "\n"
            report += "📝 **[Check List]**\n"
            report += "1. 영업이익 적자기업 제외하고 테마별로 표로 분류\n"
            report += "2. 최근 일주일간 뉴스 및 날짜 확인\n"
            report += "3. 이격도 하락 원인 분석\n"
            report += "4. 종합 판단 후 최종 종목 선정"

            send_discord_message(report)
            print(f"✅ {len(results)}개 추출 및 전송 완료.")
        else:
            send_discord_message("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        err_msg = f"❌ 프로그램 오류: {e}"
        print(err_msg)
        send_discord_message(err_msg)

if __name__ == "__main__":
    main()
