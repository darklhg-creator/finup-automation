import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def get_analysis(target_stocks, threshold):
    results = []
    for idx, row in target_stocks.iterrows():
        try:
            name = row['Name']
            code = row['Code']
            
            # 기업 설명 (Sector와 Industry 합치기)
            sector = row.get('Sector', '')
            industry = row.get('Industry', '')
            desc = f"{sector} {industry}".strip()
            if not desc: desc = "사업 정보 없음"

            # 주가 데이터 수집 및 이격도 계산
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            current_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disparity = round((current_price / ma20) * 100, 1)

            if disparity <= threshold:
                results.append({
                    'name': name,
                    'disparity': disparity,
                    'desc': desc
                })
        except:
            continue
    return results

def main():
    print("🚀 1단계 분석 시작...")
    
    try:
        df_kospi = fdr.StockListing('KOSPI')
        df_kosdaq = fdr.StockListing('KOSDAQ')
        df_total = pd.concat([df_kospi, df_kosdaq])
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return

    # 분석 범위 (상위 500개)
    target_stocks = df_total.head(500) 

    # 1차 검색 (90 이하)
    final_results = get_analysis(target_stocks, 90)
    search_range = "90 이하"

    # 2차 검색 (90 이하가 없을 때 95 이하)
    if not final_results:
        final_results = get_analysis(target_stocks, 95)
        search_range = "95 이하"

    # 결과 전송
    if final_results:
        final_results = sorted(final_results, key=lambda x: x['disparity'])
        
        report = f"### 📊 1단계 분석 ({search_range})\n"
        for r in final_results:
            # 요청하신 예시 포맷: 종목명, 이격도, 종목 설명
            report += f"{r['name']}, {r['disparity']}, {r['desc'][:60]}\n"
        
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        print(f"✅ 전송 완료 ({len(final_results)}종목)")
    else:
        print("🔍 조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    main()
