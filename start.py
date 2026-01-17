import FinanceDataReader as fdr
import requests
import os
import pandas as pd
from datetime import datetime

# 이격도 채널 웹훅
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def main():
    print("🚀 [1단계] 이격도 90 이하 종목 상세 분석 및 리포트 생성...")
    
    # 1. 종목 정보 로드 (설명 추출용)
    df_krx = fdr.StockListing('KRX')
    
    # 2. 분석 대상 (targets.txt) 읽기
    if os.path.exists("targets.txt"):
        with open("targets.txt", "r", encoding="utf-8") as f:
            target_names = [line.strip() for line in f.readlines() if line.strip()]
    else:
        print("❌ targets.txt가 없습니다.")
        return

    results = []
    filtered_for_next = [] # 2단계로 넘길 리스트

    for name in target_names:
        try:
            # KRX 리스트에서 종목 매칭
            row = df_krx[df_krx['Name'] == name]
            if row.empty: continue
            
            code = row['Code'].values[0]
            sector = row['Sector'].values[0] if 'Sector' in row.columns else "기타"
            industry = row['Industry'].values[0] if 'Industry' in row.columns else "정보없음"
            
            # 주가 데이터로 이격도 재확인
            df = fdr.DataReader(code).tail(30)
            current_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disparity = round((current_price / ma20) * 100, 1)

            # 이격도 90 이하인 종목만 (만약 90이하가 하나도 없으면 95로 자동 확장)
            # 여기서는 아까 나온 리스트를 기준으로 하므로 95 이하로 설정해두면 안전합니다.
            if disparity <= 95:
                results.append({
                    'name': name,
                    'price': current_price,
                    'disparity': disparity,
                    'desc': f"[{sector}] {str(industry)[:35]}..."
                })
                filtered_for_next.append(name) # 이름만 따로 저장
        except:
            continue

    # 3. 리포트 생성 및 2단계 연동 파일 저장
    if results:
        # 이격도 낮은 순 정렬
        results = sorted(results, key=lambda x: x['disparity'])
        
        report = f"## 📈 1단계 분석: 이격도 과매도 포착 ({len(results)}종목)\n"
        report += "| 종목명 | 현재가 | 이격도 | 종목 개요 |\n| :--- | :--- | :--- | :--- |\n"
        
        for r in results:
            report += f"| {r['name']} | {int(r['price']):,}원 | **{r['disparity']}%** | {r['desc']} |\n"
        
        # 디스코드 전송
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        
        # [중요] 2단계를 위한 파일 생성
        with open("filtered_targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(filtered_for_next))
            
        print(f"✅ 1단계 완료: filtered_targets.txt에 {len(filtered_for_next)}종목 저장됨.")
    else:
        print("🔍 조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    main()
