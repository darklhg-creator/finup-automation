import FinanceDataReader as fdr
import requests
import os
import pandas as pd
from datetime import datetime

# 이격도 채널 웹훅
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def check_market_open():
    """오늘 주식 시장이 열리는 날인지 확인"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False, "오늘은 즐거운 주말입니다. 주식 시장이 열리지 않습니다. ☕"
    try:
        df = fdr.DataReader('005930').tail(1)
        last_market_date = df.index[-1].date()
        if now.date() > last_market_date and now.hour >= 10:
            return False, "오늘은 공휴일 또는 휴장일입니다. 📅"
    except:
        return True, "개장 여부 확인 불가 (진행 시도)"
    return True, "개장일입니다."

def get_stock_info(symbol):
    """종목의 간단한 설명(업종/주요상품)을 가져옴"""
    try:
        # KRX 종목 전체 리스트에서 해당 종목 찾기
        df_krx = fdr.StockListing('KRX')
        row = df_krx[df_krx['Code'] == symbol]
        if not row.empty:
            sector = row['Sector'].values[0] if 'Sector' in row else "정보 없음"
            industry = row['Industry'].values[0] if 'Industry' in row else "정보 없음"
            return f"[{sector}] {industry}"
    except:
        return "종목 상세 정보를 불러올 수 없습니다."
    return "정보 없음"

def main():
    print("📊 시장 개장 여부 확인 중...")
    is_open, msg = check_market_open()
    
    if not is_open:
        print(f"📢 {msg}")
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': f"🔔 **휴장 안내**\n> {msg}"})
        return

    print("🚀 이격도 및 종목 분석을 시작합니다.")
    
    if not os.path.exists("targets.txt"):
        print("targets.txt 파일이 없습니다. pinup.py를 먼저 실행하세요.")
        return

    with open("targets.txt", "r", encoding="utf-8") as f:
        target_names = [line.strip() for line in f.readlines() if line.strip()]

    # KRX 전체 리스트 불러오기 (이름으로 코드 찾기용)
    df_krx = fdr.StockListing('KRX')
    
    results = []
    for name in target_names:
        try:
            # 이름으로 종목코드 찾기
            code = df_krx[df_krx['Name'] == name]['Code'].values[0]
            
            # 주가 데이터 수집 (최근 20일 이상)
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            # 이격도 계산 (20일 이동평균선 기준)
            ma20 = df['Close'].rolling(window=20).mean()
            current_price = df['Close'].iloc[-1]
            last_ma20 = ma20.iloc[-1]
            disparity = (current_price / last_ma20) * 100 # 이격도 공식
            
            # 종목 설명 가져오기
            desc = get_stock_info(code)
            
            # 결과 저장 (이격도가 너무 과열되거나 침체된 경우 등을 판단)
            results.append({
                'name': name,
                'code': code,
                'price': current_price,
                'disparity': round(disparity, 2),
                'desc': desc
            })
            print(f"✅ {name} 분석 완료")
        except:
            print(f"❌ {name} 데이터 수집 실패")

    # 분석 결과 리포트 생성
    if results:
        report = "## 📈 오늘의 이격도 분석 리포트\n"
        report += "| 종목명 | 현재가 | 이격도(20일) | 종목 설명 |\n| :--- | :--- | :--- | :--- |\n"
        for r in results:
            # 이격도 수치에 따라 강조 표시
            status = "🔥" if r['disparity'] >= 110 else "🟢"
            report += f"| {r['name']} | {format(int(r['price']), ',')}원 | {status} {r['disparity']}% | {r['desc']} |\n"
        
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        print("✅ 분석 리포트 전송 완료!")
    else:
        print("⚠️ 분석할 수 있는 데이터가 없습니다.")

if __name__ == "__main__":
    main()
