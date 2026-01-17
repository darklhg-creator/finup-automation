import FinanceDataReader as fdr
import requests
import pandas as pd

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def main():
    print("🚀 [1단계] 코스피 500 + 코스닥 500 통합 분석 시작...")
    
    try:
        # 1. 시장별로 상위 500개씩 가져와서 합치기
        df_kospi = fdr.StockListing('KOSPI').head(500)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(500)
        df_total = pd.concat([df_kospi, df_kosdaq])
        
        results = []
        print(f"📡 총 {len(df_total)}개 종목 분석 중...")

        for idx, row in df_total.iterrows():
            try:
                code = row['Code']
                name = row['Name']
                
                # 20일 데이터 로드 및 이격도 계산
                df = fdr.DataReader(code).tail(25)
                if len(df) < 20: continue
                
                curr_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                disparity = round((curr_price / ma20) * 100, 1)

                # 95 이하 종목 수집
                if disparity <= 95:
                    results.append({
                        'name': name, 
                        'code': code, 
                        'disparity': disparity
                    })
            except:
                continue

        # 2. 결과 정렬 및 전송 (요청하신 심플 양식)
        if results:
            results = sorted(results, key=lambda x: x['disparity'])
            
            report = f"### 📊 1단계 분석 결과 (코스피/코스닥 TOP 500)\n"
            for r in results[:20]: # 상위 20개 출력
                # 불필요한 정보 없이 종목명, 코드, 이격도만 표시
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}\n"
            
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
            
            with open("filtered_targets.txt", "w", encoding="utf-8") as f:
                f.write("\n".join([r['name'] for r in results]))
            print(f"✅ 분석 완료! {len(results)}종목 전송")
        else:
            print("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    main()
