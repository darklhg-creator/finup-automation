import yfinance as yf
import pandas as pd
import os
import re
import requests

# 디스코드 설정 (env에서 가져오거나 직접 입력)
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_discord_message(message):
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ 디스코드 웹훅 URL이 설정되지 않았습니다.")
        return
    
    payload = {"content": message}
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"⚠️ 디스코드 전송 실패: {e}")

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
        
        # 3. 이격도 계산
        disparity = (last_row['Close'] / last_row['MA20']) * 100
        
        # 최종 필터
        if long_term_trend and mid_term_trend and disparity <= 92.5:
            return True, round(disparity, 1)
        return False, None
        
    except Exception as e:
        print(f"⚠️ {ticker} 분석 중 오류: {e}")
        return False, None

def main():
    print("🔍 [정배열 필터링] 알짜 눌림목 종목 선별 중...")
    
    input_file = "targets.txt" 
    
    if not os.path.exists(input_file):
        print(f"❌ '{input_file}' 파일이 없습니다.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        tickers = [line.strip() for line in f.readlines() if line.strip()]

    if not tickers:
        print("📝 읽어온 종목이 없습니다.")
        return

    refined_list = []
    print(f"📋 총 {len(tickers)}개 종목 분석 시작...")
    
    for item in tickers:
        try:
            # "이름,코드" 또는 "이름(코드)" 형식 대응
            if ',' in item:
                code = item.split(',')[0].strip()
                name = item.split(',')[1].strip()
            else:
                code_match = re.search(r'\((\d+)\)', item)
                if code_match:
                    code = code_match.group(1)
                    name = item.split('(')[0]
                else:
                    code = item.strip()
                    name = item

            symbol = f"{code}.KQ"
            is_good, disp_val = check_moving_average_order(symbol)
            
            if is_good:
                refined_list.append(f"{name}({code})")
                print(f"✅ [통과] {name} (이격도: {disp_val}%)")
            else:
                print(f"➖ [탈락] {name}")
        except Exception as e:
            print(f"⚠️ {item} 처리 중 오류: {e}")
            continue

    # 결과 저장 및 메시지 전송
    if not refined_list:
        no_stock_msg = "📉 [필터링 결과] 오늘 조건(정배열+눌림목)에 맞는 종목이 없습니다. 무리한 매매 금지! ☕"
        print(no_stock_msg)
        send_discord_message(no_stock_msg)
        # 파일은 비워둡니다.
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("")
    else:
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(refined_list))
        print(f"✨ 필터링 완료! {len(refined_list)}개 생존.")

if __name__ == "__main__":
    main()
