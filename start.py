import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def get_analysis(df_total, target_stocks, threshold):
    """지정한 이격도 기준(threshold) 이하인 종목을 찾아 리스트로 반환"""
    results = []
    for idx, row in target_stocks.iterrows():
        try:
            name = row['Name']
            code = row['Code']
            
            # 기업 설명 (Sector와 Industry 합치기)
            sector = row.get('Sector', '')
            industry = row.get('Industry', '')
            desc = f"{sector} {industry}".strip()
            if not desc: desc = "주요 사업 정보 확인 중"

            # 주가 데이터 가져오기
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            # 이격도 계산 (MA20)
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
    print("🚀 [1단계] 이격도 분석 시작...")
    
    # 1. 기업 정보 데이터 로드
    try:
        df_kospi = fdr.StockListing('KOSPI')
        df_kosdaq = fdr.StockListing('KOSDAQ')
        df_total = pd.concat([df_kospi, df_kosdaq])
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return

    # 분석 범위 설정 (상위 500개)
    target_stocks = df_total.head(500) 

    # 2. 1차 검색 (이격도 90 이하)
    print("🔍 1차 검색 중: 이격도 90 이하...")
    final_results = get_analysis(df_total, target_stocks, 90)
    search_range = "90 이하"

    # 3. 90 이하가 없으면 2차 검색 (이격도 95 이하)
    if not final_results:
        print("🔍 2차 검색 중: 90 이하가 없어 95 이하로 확장합니다...")
        final_results = get_analysis(df_total, target_stocks, 95)
        search_range = "95 이하"

    # 4. 결과 리포트 생성 및 전송
    if final_results:
        # 이격도 낮은 순 정렬
        final_results = sorted(final_results, key=lambda x: x['disparity'])
        
        report = f"### 📊 1단계 이격도 분석 ({search_range} 포착)\n"
        
        for r in final_results:
            # [종목명] 이격도수치 - 설명 포맷
            report += f"**{r['name']}** : {r['disparity']}\n"
            report += f"> {r['desc'][:70]}\n\n"
        
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        print(f"✅ 분석 완료! {len(final_results)}개 종목 전송 성공")
    else:
        print("🔍 조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    main()
