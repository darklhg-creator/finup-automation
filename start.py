import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime

# 이격도 채널 웹훅
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def get_analysis(target_stocks, threshold):
    """지정한 이격도 기준 이하인 종목을 찾아 리스트로 반환"""
    results = []
    for idx, row in target_stocks.iterrows():
        try:
            name = row['Name']
            code = row['Code']
            
            # 기업 정보 결합 (Sector, Industry)
            sector = row.get('Sector', '')
            industry = row.get('Industry', '')
            desc = f"{sector} {industry}".strip()
            if not desc: desc = "사업 정보 없음"

            # 주가 데이터 수집 (최근 30일)
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            # 이격도 계산 (20일 이동평균선 기준)
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
    print("🚀 [1단계 테스트] 코스피/코스닥 상위 500개씩 분석 시작 (휴장 체크 제외)...")
    
    # 1. 데이터 로드 (코스피 500 + 코스닥 500)
    try:
        print("🔍 종목 리스트 불러오는 중...")
        df_kospi = fdr.StockListing('KOSPI').head(500)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(500)
        target_stocks = pd.concat([df_kospi, df_kosdaq])
        print(f"✅ 총 {len(target_stocks)}개 종목 분석 대기 중")
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return

    # 2. 1차 검색 (이격도 90 이하)
    print("🔍 1차 검색 중 (90 이하)...")
    final_results = get_analysis(target_stocks, 90)
    search_range = "90 이하"

    # 3. 1차 결과가 없으면 2차 검색 (이격도 95 이하)
    if not final_results:
        print("🔍 2차 검색 중 (95 이하)...")
        final_results = get_analysis(target_stocks, 95)
        search_range = "95 이하"

    # 4. 결과 리포트 전송 및 파일 저장
    if final_results:
        # 이격도 낮은 순으로 정렬
        final_results = sorted(final_results, key=lambda x: x['disparity'])
        
        report = f"### 📊 1단계 분석 ({search_range})\n"
        for r in final_results:
            # 포맷: 종목명, 이격도, 설명
            report += f"{r['name']}, {r['disparity']}, {r['desc'][:60]}\n"
        
        # 디스코드 전송
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        
        # 2단계 finance_filter.py 전달용 파일 생성
        with open("filtered_targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join([r['name'] for r in final_results]))
            
        print(f"✅ 분석 완료! {len(final_results)}종목 포착 및 전송 성공")
    else:
        print("🔍 분석 조건(95 이하)에 맞는 종목이 시장에 없습니다.")

if __name__ == "__main__":
    main()
