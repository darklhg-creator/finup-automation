import FinanceDataReader as fdr
import requests
import pandas as pd

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def main():
    print("🚀 [1단계] 초고속 모드 가동 (KOSPI 500 + KOSDAQ 500)")
    
    try:
        # 1. 시장별 리스트 로드 (시총 상위 각 500개)
        ks = fdr.StockListing('KOSPI').head(500)
        kq = fdr.StockListing('KOSDAQ').head(500)
        df_total = pd.concat([ks, kq])
        
        results = []
        # 2. 개별 종목 호출 대신, 핵심 데이터만 빠르게 추출
        print(f"📡 {len(df_total)}개 종목 분석 중... 이번엔 진짜 빠를 겁니다!")

        for idx, row in df_total.iterrows():
            code = row['Code']
            name = row['Name']
            
            try:
                # 20일선 계산을 위해 딱 25일치 데이터만 가져옴 (제일 빠른 방식)
                df = fdr.DataReader(code).tail(25)
                if len(df) < 20: continue
                
                curr_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                disparity = round((curr_price / ma20) * 100, 1)

                if disparity <= 95:
                    results.append({'name': name, 'code': code, 'disparity': disparity})
            except:
                continue

        # 3. 결과 전송 (사업 정보 제외 버전)
        if results:
            results = sorted(results, key=lambda x: x['disparity'])
            
            report = f"### 📊 1단계 분석 결과 (이격도 순)\n"
            for r in results[:20]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}\n"
            
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
            
            with open("filtered_targets.txt", "w", encoding="utf-8") as f:
                f.write("\n".join([r['name'] for r in results]))
            print(f"✅ 완료! {len(results)}종목 전송")
        else:
            print("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        print(f"❌ 에러: {e}")

if __name__ == "__main__":
    main()
