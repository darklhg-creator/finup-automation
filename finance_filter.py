import yfinance as yf
import pandas as pd
import os
import re

def check_moving_average_order(ticker):
    try:
        # 이평선을 계산하기 위해 충분한 데이터(1년치)를 가져옵니다.
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if len(df) < 120:
            return False, None
            
        # 이평선 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        
        last_row = df.iloc[-1]
        
        # 1. 중장기 정배열 조건 (60일선이 120일선 위에 있음)
        long_term_trend = last_row['MA60'] > last_row['MA120']
        
        # 2. 단기 추세 조건 (20일선이 60일선 위에 있음)
        mid_term_trend = last_row['MA20'] > last_row['MA60']
        
        # 3. 이격도 계산 (20일선 기준 현재 주가 비율)
        disparity = (last_row['Close'] / last_row['MA20']) * 100
        
        # 최종 필터: 중장기 정배열 + 단기 추세 유지 + 이격도 과매도 구간(92.5 이하)
        if long_term_trend and mid_term_trend and disparity <= 92.5:
            return True, round(disparity, 1)
        return False, None
        
    except Exception as e:
        print(f"⚠️ {ticker} 분석 중 오류: {e}")
        return False, None

def main():
    print("🔍 [정배열 필터링] 알짜 눌림목 종목 선별 중...")
    
    # 1단계(start.py)에서 생성한 결과 파일 이름을 확인합니다.
    input_file = "targets.txt" 
    
    if not os.path.exists(input_file):
        print(f"❌ '{input_file}' 파일이 없습니다. start.py가 정상적으로 실행되었는지 확인해주세요.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        tickers = [line.strip() for line in f.readlines() if line.strip()]

    if not tickers:
        print("📝 읽어온 종목이 없습니다. 필터링을 종료합니다.")
        return

    refined_list = []
    print(f"📋 총 {len(tickers)}개 종목 분석 시작...")
    
    for item in tickers:
        try:
            # "종목명(코드)" 형식에서 코드만 추출 (정규표현식 사용)
            code_match = re.search(r'\((\d+)\)', item)
            if not code_match:
                code = item.strip()
                name = item
            else:
                code = code_match.group(1)
                name = item.split('(')[0]

            # 한국 시장 종목 코드는 6자리 숫자이므로 .KQ(코스닥) 또는 .KS(코스피) 필요
            # 여기서는 기본적으로 코스닥(.KQ)을 시도합니다.
            symbol = f"{code}.KQ"
            
            is_good, disp_val = check_moving_average_order(symbol)
            if is_good:
                refined_list.append(f"{name}({code})")
                print(f"✅ [통과] {name} (이격도: {disp_val}%)")
            else:
                print(f"➖ [탈락] {name}")
        except Exception as e:
            print(f"⚠️ {item} 처리 중 건너뜀: {e}")
            continue

    # 3. 최종 필터링된 결과를 다시 targets.txt에 저장 (기존 리스트를 덮어씀)
    with open("targets.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(refined_list))
    
    print(f"✨ 필터링 완료! {len(refined_list)}개 종목이 최종 생존했습니다.")

if __name__ == "__main__":
    main()
