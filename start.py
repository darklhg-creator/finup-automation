import FinanceDataReader as fdr
import requests
import os
import pandas as pd
from datetime import datetime

# 이격도 채널 웹훅
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def get_stock_data(target_names, df_krx, threshold):
    """지정한 이격도(threshold) 이하인 종목들을 추출합니다."""
    results = []
    for name in target_names:
        try:
            row = df_krx[df_krx['Name'] == name]
            if row.empty: continue
            
            code = row['Code'].values[0]
            sector = row['Sector'].values[0] if 'Sector' in row.columns else "분류없음"
            industry = row['Industry'].values[0] if 'Industry' in row.columns else "내용없음"
            
            # 주가 데이터 수집 (최근 40일치)
            df = fdr.DataReader(code).tail(40)
            if len(df) < 20: continue
            
            # 이격도 계산
            current_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disparity = round((current_price / ma20) * 100, 1)

            # 설정한 기준값 이하인 경우만 수집
            if disparity <= threshold:
                results.append({
                    'name': name,
                    'price': current_price,
                    'disparity': disparity,
                    'desc': f"[{sector}] {str(industry)[:30]}..."
                })
        except:
            continue
    return results

def main():
    print("🚀 [테스트 모드] 이격도 분석을 시작합니다. (휴장일 체크 건너뜀)")
    
    # 1. KRX 상장사 정보 로드
    df_krx = fdr.StockListing('KRX')
    
    # 분석 대상 로드 (targets.txt 기반)
    if os.path.exists("targets.txt"):
        with open("targets.txt", "r", encoding="utf-8") as f:
            target_names = [line.strip() for line in f.readlines() if line.strip()]
    else:
        print("❌ targets.txt 파일이 없습니다. 먼저 pinup.py 등을 통해 파일을 생성해주세요.")
        return

    # 2. 이격도 검색 (1순위: 90 이하)
    print("🔍 1차 검색 중: 이격도 90 이하...")
    final_results = get_stock_data(target_names, df_krx, 90)
    
    # 90 이하가 없으면 2순위 검색 (95 이하)
    if not final_results:
        print("🔍 2차 검색 중: 이격도 90 이하가 없어 95 이하로 검색합니다.")
        final_results = get_stock_data(target_names, df_krx, 95)

    # 3. 결과 알림
    if final_results:
        # 이격도 낮은 순 정렬
        final_results = sorted(final_results, key=lambda x: x['disparity'])
        
        # 메시지 작성
        report = f"## 📈 1단계 이격도 분석 결과 ({'90이하' if any(r['disparity']<=90 for r in final_results) else '95이하'})\n"
        report += "| 종목명 | 현재가 | 이격도 | 종목 설명 |\n| :--- | :--- | :--- | :--- |\n"
        
        for r in final_results:
            report += f"| {r['name']} | {int(r['price']):,}원 | **{r['disparity']}** | {r['desc']} |\n"
        
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        print(f"✅ 분석 완료! {len(final_results)}개 종목 전송 성공")
    else:
        print("🔍 분석 조건(이격도 95 이하)에 맞는 종목이 하나도 없습니다.")

if __name__ == "__main__":
    main()
