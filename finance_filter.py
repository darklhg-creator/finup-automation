import yfinance as yf
import pandas as pd
import os

def check_moving_average_order(ticker):
    try:
        # 이평선을 계산하기 위해 충분한 데이터(6개월치)를 가져옵니다.
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if len(df) < 120:
            return False
            
        # 이평선 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        
        last_row = df.iloc[-1]
        
        # 1. 중장기 정배열 조건 (60일선이 120일선 위에 있음)
        # 이 조건이 맞아야 '하락 추세'인 브이티 같은 종목이 걸러집니다.
        long_term_trend = last_row['MA60'] > last_row['MA120']
        
        # 2. 단기 눌림목 조건 (20일선이 60일선 위에 있음)
        # 주가가 일시적으로 20일선 밑으로 내려왔더라도 추세는 살아있어야 함
        mid_term_trend = last_row['MA20'] > last_row['MA60']
        
        # 3. 이격도 계산 (20일선 기준 92% 이하인지 확인 - start.py와 연동)
        disparity = (last_row['Close'] / last_row['MA20']) * 100
        
        # 최종 필터: 중장기 정배열 + 이격도 과매도 구간
        if long_term_trend and mid_term_trend and disparity <= 92.5:
            return True, round(disparity, 1)
        return False, None
        
    except Exception as e:
        print(f"⚠️ {ticker} 분석 중 오류: {e}")
        return False, None

def main():
    print("🔍 [정배열 필터링] 알짜 눌림목 종목 선별 중...")
    
    # targets.txt에 있는 종목들을 읽어옵니다.
    if not os.path.exists("targets_raw.txt"):
        print("파일이 없습니다.")
        return

    with open("targets_raw.txt", "r", encoding="utf-8") as f:
        tickers = [line.strip() for line in f.readlines()]

    refined_list = []
    
    for item in tickers:
        # 종목코드와 이름 분리 (예: "태성(323280)")
        try:
            name = item.split('(')[0]
            code = item.split('(')[1].replace(')', '')
            symbol = f"{code}.KQ" if int(code) > 0 else f"{code}.KS" # 코스닥/코스피 구분 로직 필요시 추가
            
            is_good, disp_val = check_moving_average_order(f"{code}.KQ") # 기본 코스닥 가정
            if is_good:
                refined_list.append(f"{name}({code}): {disp_val}")
                print(f"✅ 통과: {name} (이격도: {disp_val})")
        except:
            continue

    # 최종 필터링된 결과 저장
    with open("targets.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(refined_list))
    
    print(f"✨ 필터링 완료! {len(refined_list)}개 종목이 살아남았습니다.")

if __name__ == "__main__":
    main()
