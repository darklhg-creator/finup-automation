import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def main():
    print("🚀 [1단계] 고속 분석 모드 가동 (KOSPI/KOSDAQ 상위 1000개)")
    
    try:
        # 1. 종목 리스트 및 상세정보 가져오기
        df_kospi = fdr.StockListing('KOSPI').head(500)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(500)
        df_total = pd.concat([df_kospi, df_kosdaq])
        
        # 2. 모든 종목의 현재가 데이터를 한 번에 가져오기 (이게 핵심입니다)
        # KRX 전체 종목의 현재가와 20일 이동평균선을 계산하기 위한 종가 데이터
        print("📊 시장 데이터 수집 중...")
        
        results = []
        for idx, row in df_total.iterrows():
            code = row['Code']
            name = row['Name']
            
            # 한 종목씩 DataReader를 호출하지 않고, 내부 계산 로직 최소화
            try:
                # 20일선 계산을 위해 최근 데이터만 슬라이싱해서 가져옴
                df = fdr.DataReader(code).tail(25) 
                if len(df) < 20: continue
                
                curr_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                disparity = round((curr_price / ma20) * 100, 1)
                
                if disparity <= 95:
                    desc = row.get('Sector', row.get('Industry', '사업 정보 확인 중'))
                    results.append({
                        'name': name,
                        'code': code,
                        'disparity': disparity,
                        'desc': desc
                    })
            except:
                continue

        # 3. 결과 필터링 및 전송
        # 90 이하가 있으면 90 이하만, 없으면 95 이하 출력
        low_disparity = [r for r in results if r['disparity'] <= 90]
        final_list = low_disparity if low_disparity else results
        search_range = "90 이하" if low_disparity else "95 이하"

        if final_list:
            final_list = sorted(final_list, key=lambda x: x['disparity'])
            
            report = f"### 📊 1단계 분석 ({search_range})\n"
            for r in final_list[:20]: # 너무 길어지지 않게 상위 20개만
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}\n"
                report += f"  └ {str(r['desc'])[:60]}\n\n"
            
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
            
            with open("filtered_targets.txt", "w", encoding="utf-8") as f:
                f.write("\n".join([r['name'] for r in final_list]))
            print(f"✅ 분석 완료! {len(final_list)}종목 전송")
        else:
            print("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    main()
