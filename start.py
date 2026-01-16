import FinanceDataReader as fdr
import pandas as pd
import requests
import os
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def is_market_open():
    """오늘이 한국 주식시장 개장일인지 확인"""
    # KRX는 개장일 데이터를 제공합니다.
    now = datetime.now()
    # 오늘 날짜의 개장 여부 확인 (가장 편한 방법은 FDR로 오늘 데이터를 시도해보는 것)
    try:
        # 삼성전자 데이터를 가져와서 마지막 날짜가 오늘인지 확인
        df = fdr.DataReader('005930', now.strftime('%Y-%m-%d'), now.strftime('%Y-%m-%d'))
        if df.empty:
            return False
        return True
    except:
        return False

def main():
    print("📅 시장 개장 여부 확인 중...")
    
    # 1. 공휴일 체크 로직
    # 평일(월-금)이지만 한국거래소 휴장일인 경우 종료
    # (단, FDR 데이터 업데이트 시간에 따라 장중에는 데이터가 안 잡힐 수 있으므로 
    #  안전하게 한국거래소 휴장일 리스트를 체크하는 방식이 좋으나, 
    #  가장 간단한 건 평일 체크 후 FDR의 응답을 보는 것입니다.)
    
    # 실제 개장일 확인이 까다로우므로, 
    # 5시 실행 시점에 오늘 날짜 데이터가 생성되었는지 확인하는 것이 가장 정확합니다.
    try:
        check_df = fdr.DataReader('005930', datetime.now().strftime('%Y%m%d'))
        if check_df.empty:
            print("❌ 오늘은 주식시장 휴장일(공휴일)입니다. 프로그램을 종료합니다.")
            return
    except:
        print("❌ 휴장일 판별 중 오류 발생 또는 휴장일입니다.")
        return

    print("🔍 1단계: 이격도 분석 시작...")
    df_krx = fdr.StockListing('KRX')
    df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
    
    codes, names = df_top500['Code'].tolist(), df_top500['Name'].tolist()
    under_95 = []

    for i, code in enumerate(codes):
        try:
            df = fdr.DataReader(code).tail(25)
            curr = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disp = (curr / ma20) * 100
            
            if disp <= 95:
                under_95.append(f"{code},{names[i]}")
        except: continue

    # 다음 단계를 위해 파일 저장 (2, 3단계는 이 파일이 있어야 작동함)
    if under_95:
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(under_95))
        requests.post(DISCORD_WEBHOOK_URL, data={'content': f"✅ 1단계 완료: 후보군 {len(under_95)}개 추출됨."})
    else:
        # 후보가 없으면 targets.txt를 삭제하여 다음 단계가 실행 안 되게 함
        if os.path.exists("targets.txt"):
            os.remove("targets.txt")
        requests.post(DISCORD_WEBHOOK_URL, data={'content': "ℹ️ 오늘은 이격도 조건에 맞는 종목이 없습니다."})

if __name__ == "__main__":
    main()
