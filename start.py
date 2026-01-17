import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime

# 이격도 채널 웹훅
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def check_market_open():
    """개장 확인 (테스트를 위해 토요일에도 분석은 진행하도록 설정)"""
    now = datetime.now()
    if now.weekday() >= 5:
        # 주말임을 알리지만, 테스트를 위해 True를 반환하게 할 수 있습니다. 
        # 실제 운영시에는 return False로 바꾸시면 됩니다.
        return True, "오늘은 주말이지만 테스트를 위해 분석을 진행합니다. ☕"
    return True, "개장일입니다."

def main():
    print("🚀 [1단계] 전체 시장 이격도 분석 시작...")
    
    # 1. 개장 확인
    is_open, open_msg = check_market_open()
    print(f"📢 {open_msg}")

    # 2. 상장 종목 리스트 로드
    try:
        print("🔍 상장 종목 리스트 로드 중...")
        df_krx = fdr.StockListing('KRX')
    except Exception as e:
        print(f"❌ 리스트 로드 실패: {e}")
        return

    # 3. 사용 가능한 설명 컬럼 찾기 (안전장치)
    # 'Sector', 'Industry', 'Group' 등 데이터에 포함된 컬럼 중 하나를 선택
    possible_cols = ['Sector', 'Industry', 'Description', 'Group']
    available_col = next((c for c in possible_cols if c in df_krx.columns), None)
    print(f"✅ 사용 가능한 설명 컬럼: {available_col}")

    results = []
    # 분석 범위 (속도를 위해 우선 상위 400개)
    target_stocks = df_krx.head(400) 
    
    print(f"📡 {len(target_stocks)}개 종목 분석 시작 (이격도 90 이하 탐색)")

    for idx, row in target_stocks.iterrows():
        try:
            name = row['Name']
            code = row['Code']
            
            # 설명 가져오기 (컬럼이 아예 없으면 '내용없음' 처리)
            desc = "상세 정보 없음"
            if available_col:
                val = row[available_col]
                desc = val if pd.notna(val) else "상세 정보 없음"

            # 주가 데이터 가져오기
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            # 이격도 계산 (MA20 기준)
            current_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disparity = round((current_price / ma20) * 100, 1)

            # 90 이하 포착 (없을 경우를 대비해 95까지 일단 수집)
            if disparity <= 95:
                results.append({
                    'name': name,
                    'price': current_price,
                    'disparity': disparity,
                    'desc': f"{str(desc)[:30]}..."
                })
        except Exception:
            continue # 오류 나면 그냥 다음 종목으로

    # 4. 리포트 생성 및 전송
    if results:
        # 이격도 낮은 순으로 정렬
        results = sorted(results, key=lambda x: x['disparity'])
        
        # 90 이하와 95 이하를 구분해서 보여줌
        report = f"## 📈 [1단계] 시장 이격도 분석 ({datetime.now().strftime('%m/%d')})\n"
        report += "| 종목명 | 현재가 | 이격도 | 종목 설명 |\n| :--- | :--- | :--- | :--- |\n"
        
        for r in results[:15]: # 너무 길면 잘림 방지 (상위 15개)
            status = "🔵" if r['disparity'] <= 90 else "🟢"
            report += f"| {r['name']} | {int(r['price']):,}원 | {status} **{r['disparity']}%** | {r['desc']} |\n"
        
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        print(f"✅ 분석 완료! 포착된 종목: {len(results)}개")
    else:
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': "🔍 **1단계 분석**: 조건(95 이하)에 맞는 종목이 없습니다."})

if __name__ == "__main__":
    main()
