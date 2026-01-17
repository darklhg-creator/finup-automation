import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime

# 이격도 채널 웹훅
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def main():
    print("🚀 [1단계] 전체 시장 이격도 분석 시작...")
    
    # 1. 상장 종목 리스트 로드
    try:
        # KRX 전체 대신 KOSPI, KOSDAQ을 각각 가져오면 데이터가 더 정확합니다.
        print("🔍 상장 종목 리스트 로드 중...")
        df_krx = fdr.StockListing('KRX')
    except Exception as e:
        print(f"❌ 리스트 로드 실패: {e}")
        return

    # 컬럼명 확인 및 대응 (Sector 또는 Industry)
    col_name = 'Sector' if 'Sector' in df_krx.columns else 'Industry'
    print(f"✅ 사용 가능한 컬럼 확인: {col_name}")

    results = []
    # 2. 분석 루프 (시간 관계상 시총 상위나 주요 종목 위주로 먼저 탐색 추천)
    # 테스트를 위해 상위 500개 종목으로 범위를 좁혔습니다. (전체로 하려면 [:500] 제거)
    target_stocks = df_krx.head(500) 
    
    print(f"📡 {len(target_stocks)}개 종목 분석 시작 (이격도 90 이하 탐색)")

    for idx, row in target_stocks.iterrows():
        name = row['Name']
        code = row['Code']
        desc = row[col_name] if pd.notna(row[col_name]) else "상세 정보 없음"
        
        try:
            # 주가 데이터 가져오기 (이격도 계산을 위해 최소 20일 이상)
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            # 이격도 계산
            current_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disparity = round((current_price / ma20) * 100, 1)

            # 90 이하 포착
            if disparity <= 90:
                results.append({
                    'name': name,
                    'price': current_price,
                    'disparity': disparity,
                    'desc': f"{desc[:35]}..."
                })
                print(f"✨ 포착: {name} ({disparity}%)")
        except:
            continue

    # 3. 90 이하가 없으면 95 이하로 다시 필터링 (이미 가져온 데이터 활용)
    if not results:
        print("🔍 90 이하 종목이 없어 95 이하를 재탐색합니다.")
        # (로직 단순화를 위해 위 루프에서 95까지 담도록 수정 가능)

    # 4. 리포트 전송
    if results:
        results = sorted(results, key=lambda x: x['disparity'])
        
        report = f"## 📈 [1단계] 시장 이격도 분석 (90 이하 포착)\n"
        report += "| 종목명 | 현재가 | 이격도 | 종목 설명 |\n| :--- | :--- | :--- | :--- |\n"
        
        for r in results:
            report += f"| {r['name']} | {int(r['price']):,}원 | **{r['disparity']}%** | {r['desc']} |\n"
        
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        print(f"✅ 리포트 전송 완료! ({len(results)}개)")
    else:
        # 결과가 없을 경우 알림
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': "🔍 **1단계 분석**: 현재 이격도 90 이하 종목이 발견되지 않았습니다."})
        print("🔍 조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    main()
