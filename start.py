import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime

# 이격도 채널 웹훅
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def main():
    print("🚀 [1단계] 전체 시장 이격도 분석 시작 (90 이하 타겟)...")
    
    # 1. 전체 상장 종목 리스트 불러오기 (KOSPI, KOSDAQ)
    print("🔍 상장 종목 리스트 로드 중...")
    df_krx = fdr.StockListing('KRX')
    
    # 분석 속도를 위해 시가총액 상위 일부 또는 전체 종목 리스트업
    # 여기서는 전체 리스트(df_krx)를 순회합니다.
    all_stocks = df_krx.dropna(subset=['Sector']) # 업종 정보가 있는 종목 위주
    
    results = []
    count = 0
    total = len(all_stocks)

    print(f"📡 총 {total}개 종목 분석을 시작합니다. (이격도 90 이하 탐색)")

    for idx, row in all_stocks.iterrows():
        name = row['Name']
        code = row['Code']
        sector = row['Sector']
        industry = row['Industry'] if pd.notna(row['Industry']) else "내용 없음"
        
        try:
            # 2. 최근 주가 데이터 수집 (마지막 영업일 기준)
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            # 3. 이격도 계산 (현재가 / 20일 이동평균 * 100)
            current_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disparity = round((current_price / ma20) * 100, 1)

            # 4. 이격도 90 이하 종목 수집
            if disparity <= 90:
                results.append({
                    'name': name,
                    'price': current_price,
                    'disparity': disparity,
                    'desc': f"[{sector}] {str(industry)[:30]}..."
                })
                print(f"✨ 포착: {name} ({disparity}%)")
        except:
            continue
            
        count += 1
        if count % 100 == 0:
            print(f"⏳ 진행 중... ({count}/{total})")

    # 5. 결과 리포트 전송
    if not results:
        # 90 이하가 없으면 95 이하로 재탐색하거나 알림
        print("🔍 이격도 90 이하 종목이 없어 95 이하로 범위를 넓혀 확인합니다.")
        # (이 부분은 필요시 다시 루프를 돌리거나 threshold만 조정 가능합니다.)

    if results:
        # 이격도 낮은 순으로 정렬
        results = sorted(results, key=lambda x: x['disparity'])
        
        report = "## 📈 [1단계] 전체 시장 이격도 분석 (90 이하 포착)\n"
        report += "| 종목명 | 현재가 | 이격도 | 종목 설명 |\n| :--- | :--- | :--- | :--- |\n"
        
        for r in results:
            report += f"| {r['name']} | {format(int(r['price']), ',')}원 | **{r['disparity']}%** | {r['desc']} |\n"
        
        # 디스코드 전송 (내용이 길면 나눠서 전송해야 할 수 있음)
        if len(report) > 2000:
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': report[:1900] + "\n(이하 생략)"})
        else:
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
            
        print(f"✅ 리포트 전송 완료! 총 {len(results)}개 종목 포착")
    else:
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': "🔍 **1단계 분석**: 현재 시장에 이격도 90 이하 종목이 없습니다."})

if __name__ == "__main__":
    main()
