import FinanceDataReader as fdr
import requests
import os
import pandas as pd
from datetime import datetime

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def get_stock_info(symbol, df_krx):
    try:
        row = df_krx[df_krx['Code'] == symbol]
        if not row.empty:
            sector = row['Sector'].values[0] if 'Sector' in row else "분류없음"
            industry = row['Industry'].values[0] if 'Industry' in row else "내용없음"
            return f"[{sector}] {industry}"
    except:
        return "정보 없음"
    return "정보 없음"

def main():
    print("🧪 [테스트 모드] 최근 영업일 데이터로 검증을 시작합니다...")
    
    if not os.path.exists("targets.txt"):
        print("targets.txt 파일이 없습니다. pinup.py를 먼저 실행해 주세요.")
        return

    with open("targets.txt", "r", encoding="utf-8") as f:
        target_names = [line.strip() for line in f.readlines() if line.strip()]

    print("🔍 종목 리스트 불러오기 중...")
    df_krx = fdr.StockListing('KRX')
    
    results = []
    for name in target_names:
        try:
            # 이름으로 코드 찾기 (정확한 매칭)
            matched = df_krx[df_krx['Name'] == name]
            if matched.empty: continue
            code = matched['Code'].values[0]
            
            # 주가 데이터 수집 (날짜 지정 없이 가져와서 마지막 30일 사용)
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            # 이격도 계산
            ma20 = df['Close'].rolling(window=20).mean()
            current_price = df['Close'].iloc[-1]
            last_ma20 = ma20.iloc[-1]
            disparity = (current_price / last_ma20) * 100
            
            desc = get_stock_info(code, df_krx)
            
            results.append({
                'name': name, 'price': current_price,
                'disparity': round(disparity, 2), 'desc': desc
            })
            print(f"✅ {name} 분석 완료 (이격도: {round(disparity, 2)}%)")
        except Exception as e:
            print(f"❌ {name} 분석 실패: {e}")

    if results:
        report = f"## 📈 이격도 분석 리포트 (검증 모드)\n"
        report += "| 종목명 | 현재가 | 이격도(20일) | 종목 설명 |\n| :--- | :--- | :--- | :--- |\n"
        for r in results:
            status = "🔥" if r['disparity'] >= 110 else "🟢"
            report += f"| {r['name']} | {format(int(r['price']), ',')}원 | {status} {r['disparity']}% | {r['desc']} |\n"
        
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        print("✅ 디스코드로 검증 리포트를 전송했습니다!")

if __name__ == "__main__":
    main()
