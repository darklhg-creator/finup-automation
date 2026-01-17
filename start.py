import FinanceDataReader as fdr
import requests
import os
import pandas as pd
from datetime import datetime

# 이격도 채널 웹훅 (1단계 분석 결과 전송용)
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def get_stock_description(symbol, df_krx):
    """KRX 리스트에서 종목의 섹터와 주요 사업 내용을 가져옵니다."""
    try:
        row = df_krx[df_krx['Code'] == symbol]
        if not row.empty:
            sector = row['Sector'].values[0] if 'Sector' in row else "미분류"
            industry = row['Industry'].values[0] if 'Industry' in row else "내용 없음"
            return f"[{sector}] {industry}"
    except:
        return "정보를 가져올 수 없습니다."
    return "정보 없음"

def main():
    print("🚀 [1단계] 이격도 분석 및 종목 정보 수집 시작...")
    
    # 분석 대상 (예: 코스피/코스닥 전체 혹은 특정 리스트)
    # 여기서는 예시로 KRX 전체 종목 중 거래량이 활발한 상위 종목을 가정하거나 
    # 기존에 정의된 targets.txt가 있다면 그것을 읽어옵니다.
    
    df_krx = fdr.StockListing('KRX')
    
    # 테스트를 위해 분석할 종목 리스트 (실제로는 전략에 맞는 종목 리스트를 넣으세요)
    # 예: target_codes = ['005930', '000660', ...] 
    # 만약 targets.txt가 입구라면 아래를 사용합니다.
    if os.path.exists("targets.txt"):
        with open("targets.txt", "r", encoding="utf-8") as f:
            target_names = [line.strip() for line in f.readlines() if line.strip()]
    else:
        print("💡 분석 대상(targets.txt)이 없어 시가총액 상위 일부로 테스트합니다.")
        target_names = df_krx.head(10)['Name'].tolist()

    results = []
    for name in target_names:
        try:
            # 종목 코드로 변환
            matched = df_krx[df_krx['Name'] == name]
            if matched.empty: continue
            code = matched['Code'].values[0]
            
            # 주가 데이터 수집 및 이격도 계산
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            ma20 = df['Close'].rolling(window=20).mean()
            current_price = df['Close'].iloc[-1]
            last_ma20 = ma20.iloc[-1]
            disparity = (current_price / last_ma20) * 100
            
            # 종목 설명 추가
            desc = get_stock_description(code, df_krx)
            
            results.append({
                'name': name,
                'price': current_price,
                'disparity': round(disparity, 2),
                'desc': desc
            })
            print(f"✅ {name} 분석 완료")
        except Exception as e:
            print(f"❌ {name} 분석 중 오류: {e}")

    # 리포트 생성 및 전송
    if results:
        report = "## 📊 1단계 이격도 분석 리포트\n"
        report += "| 종목명 | 현재가 | 이격도(20일) | 종목 개요 |\n| :--- | :--- | :--- | :--- |\n"
        for r in results:
            status = "🔍" if 95 <= r['disparity'] <= 105 else "⚠️"
            report += f"| {r['name']} | {format(int(r['price']), ',')}원 | {status} {r['disparity']}% | {r['desc']} |\n"
        
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        print("✅ 1단계 분석 리포트 전송 완료!")
    else:
        print("❌ 분석된 종목이 없습니다.")

if __name__ == "__main__":
    main()
