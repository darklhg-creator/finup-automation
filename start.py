import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime
import os

# 디스코드 설정
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def main():
    print("🚀 [1단계] 정밀 분석 시작 (KOSPI 500 + KOSDAQ 500)")
    
    try:
        # [수정] 들여쓰기 정렬 및 휴장일 체크 로직
        check_df = fdr.DataReader('005930').tail(1)
        last_date = check_df.index[-1].strftime('%Y-%m-%d')
        today_date = datetime.now().strftime('%Y-%m-%d')

        if last_date != today_date:
            msg = f"📅 오늘은 주식 시장 휴무일이거나 데이터가 아직 업데이트되지 않았습니다. ({today_date})"
            print(msg)
            # 휴장일일 때는 디스코드로 알리고 종료 (선택 사항)
            # requests.post(IGYEOK_WEBHOOK_URL, json={'content': msg})
            # return # 실제 장 마감 후 실행한다면 이 부분을 주석 해제하세요.

        # 1. 대상 종목 선정
        print("📋 종목 리스트 불러오는 중...")
        df_kospi = fdr.StockListing('KOSPI').head(500)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(500)
        df_total = pd.concat([df_kospi, df_kosdaq])
        
        results = []
        print(f"📡 총 {len(df_total)}개 종목 분석 중...")

        for idx, row in df_total.iterrows():
            code = row['Code']
            name = row['Name']
            
            try:
                # 정확한 MA20을 위해 데이터를 충분히 가져옵니다.
                df = fdr.DataReader(code).tail(30)
                if len(df) < 20: 
                    continue
                
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                
                if ma20 == 0 or pd.isna(ma20):
                    continue
                    
                disparity = round((current_price / ma20) * 100, 1)

                # 이격도 95 이하 종목 수집
                if disparity <= 95.0:
                    results.append({'name': name, 'code': code, 'disparity': disparity})
            except:
                continue

        # 2. 결과 정렬 및 전송
        if results:
            # 이격도 낮은 순으로 정렬
            results = sorted(results, key=lambda x: x['disparity'])
            
            report = f"### 📊 1단계 정밀 분석 결과 (이격도 95 이하)\n"
            # 최대 30개까지만 리포트에 표시
            for r in results[:30]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}%\n"
            
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
            
            # targets.txt 저장 (finance_filter.py 전달용)
            with open("targets.txt", "w", encoding="utf-8") as f:
                # '468530,프로티나' 형식으로 저장
                lines = [f"{r['code']},{r['name']}" for r in results]
                f.write("\n".join(lines))
            
            print(f"✅ 분석 완료! {len(results)}개 종목 발견.")
        else:
            msg = "🔍 조건(이격도 95 이하)에 맞는 종목이 없습니다."
            print(msg)
            # requests.post(IGYEOK_WEBHOOK_URL, json={'content': msg})

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    main()
