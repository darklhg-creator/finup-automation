import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def main():
    print("🚀 [1단계] 정밀 분석 시작 (KOSPI 50 + KOSDAQ 50)")
    
    try:
        # [추가] 휴장일 체크: 삼성전자 데이터를 통해 오늘 장이 열렸는지 확인
        #check_df = fdr.DataReader('005930').tail(1)
        #last_date = check_df.index[-1].strftime('%Y-%m-%d')
        #today_date = datetime.now().strftime('%Y-%m-%d')

        #if last_date != today_date:
            #msg = f"📅 오늘은 주식 시장 휴무일입니다. ({today_date})"
            #print(msg)
            #requests.post(IGYEOK_WEBHOOK_URL, json={'content': msg})
            #return # 프로그램 종료

        # 1. 대상 종목 선정
        df_kospi = fdr.StockListing('KOSPI').head(50)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(50)
        df_total = pd.concat([df_kospi, df_kosdaq])
        
        results = []
        print(f"📡 총 {len(df_total)}개 종목 분석 중...")

        for idx, row in df_total.iterrows():
            code = row['Code']
            name = row['Name']
            
            try:
                # 정확한 MA20을 위해 30일치 데이터 요청
                df = fdr.DataReader(code).tail(30)
                if len(df) < 20: continue
                
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                disparity = round((current_price / ma20) * 100, 1)

                if disparity <= 95:
                    results.append({'name': name, 'code': code, 'disparity': disparity})
            except:
                continue

# 2. 결과 정렬 및 전송
        if results:
            results = sorted(results, key=lambda x: x['disparity'])
            report = f"### 📊 1단계 정밀 분석 결과\n"
            for r in results[:20]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}\n"
            
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
            
            # targets.txt 저장 (if results 안에 있어야 합니다)
            with open("targets.txt", "w", encoding="utf-8") as f:
                # '290650,엘앤씨바이오' 이런 형식으로 한 줄씩 저장합니다.
                lines = [f"{r['code']},{r['name']}" for r in results]
                f.write("\n".join(lines))
            
            print(f"✅ 분석 완료!")
        else:
            print("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    main()
