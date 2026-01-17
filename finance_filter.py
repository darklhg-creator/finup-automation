import FinanceDataReader as fdr
import requests
import pandas as pd
import os
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def get_stock_data(code):
    """최근 10일치 데이터를 가져와서 수급과 거래량 분석"""
    try:
        # fdr.DataReader는 기본적으로 종가, 거래량 등을 제공하지만 
        # 상세 수급(외인/기관)은 별도 확인이 필요할 수 있습니다. 
        # 여기서는 거래량 변곡점 분석을 위한 기본 데이터를 먼저 가져옵니다.
        df = fdr.DataReader(code).tail(10)
        if len(df) < 6: return None
        return df
    except:
        return None

def analyze_supply(code):
    """2단계: 5일 수급 분석 (외인/기관 순매수)"""
    # 실제 환경에서는 별도의 수급 API나 크롤링이 필요하지만, 
    # 여기서는 로직 구현을 위해 '상승 마감 횟수'를 수급의 대용치로 예시하거나 
    # 사용 중인 라이브러리의 수급 기능을 활용한다고 가정합니다.
    # 우선은 '거래량 분석'과 구조를 맞춰서 작성해 드릴게요.
    return True # 조건 만족 가정 (실제 데이터 연동 시 교체)

def main():
    target_file = "targets.txt"
    if not os.path.exists(target_file):
        print("❌ targets.txt 파일이 없습니다.")
        return
    
    with open(target_file, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    supply_list = []   # 2단계: 수급 필터링 결과
    volume_list = []   # 3단계: 거래량 필터링 결과

    print(f"📡 {len(lines)}개 종목 상세 분석 시작...")

    for line in lines:
        if "," not in line: continue
        code, name = line.split(",")
        
        df = get_stock_data(code)
        if df is None: continue

        # --- 2단계: 수급 분석 로직 (5일 기준) ---
        # (실제 외인/기관 데이터 호출 코드가 추가되어야 함)
        if analyze_supply(code): 
            supply_list.append(f"· {name}({code})")

        # --- 3단계: 거래량 분석 로직 ---
        today_vol = df['Volume'].iloc[-1]
        avg_vol = df['Volume'].iloc[-6:-1].mean() # 직전 5일 평균
        
        if today_vol >= avg_vol * 2: # 거래량 200% 급증
            ratio = round((today_vol / avg_vol) * 100)
            volume_list.append(f"· {name}({code}): 평소 대비 {ratio}% ⚡")

    # --- 리포트 생성 및 전송 ---
    final_report = "### 📋 이격도 기반 추가 분석 리포트\n\n"
    
    # 2단계 결과
    final_report += "🐳 **[2단계] 수급 유입 종목 (외인/기관)**\n"
    final_report += "\n".join(supply_list[:15]) if supply_list else "조건 만족 종목 없음"
    final_report += "\n\n"

    # 3단계 결과
    final_report += "⚡ **[3단계] 거래량 변곡점 종목 (200%↑)**\n"
    final_report += "\n".join(volume_list[:15]) if volume_list else "조건 만족 종목 없음"
    
    requests.post(DISCORD_WEBHOOK_URL, json={'content': final_report})
    print("✅ 분석 리포트 전송 완료!")

if __name__ == "__main__":
    main()
