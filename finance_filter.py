import yfinance as yf
import pandas as pd
import os
import re
import requests

# 디스코드 설정
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

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
        # 이평선을 계산하기 위해 데이터를 가져옵니다.
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if len(df) < 120:
            return False, None
            
        # 이평선 계산
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        
        last_row = df.iloc[-1]
        
        # [수정된 로직] 태성 같은 종목을 잡기 위한 조건
        # 1. 중장기 정배열 (60 > 120): 이건 '우상향'의 최소 조건입니다.
        long_term_trend = last_row['MA60'] > last_row['MA120']
        
        # 2. 60일선 기울기 확인: 60일선이 하향 중이면 탈락 (진짜 하락장 방지)
        # 최근 5일 전보다 60일선이 높아야 함
        ma60_is_rising = last_row['MA60'] > df['MA60'].iloc[-5]
        
        # 3. 이격도 계산 (20일선 기준)
        disparity = (last_row['Close'] / last_row['MA20']) * 100
        
        # 4. 필터링 결정
        # 이제 20일선이 60일선보다 낮아도(눌림목이어도) 60>120 정배열이면 통과시킵니다.
        if long_term_trend and ma60_is_rising and disparity <= 93.0:
            return True, round(disparity, 1)
        return False, None
        
    except Exception as e:
        print(f"⚠️ {ticker} 분석 중 오류: {e}")
        return False, None

def main():
    print("🔍 [느슨한 정배열 필터링] 추세 살아있는 눌림목 선별 중...")
    
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
            # "코드,이름" 또는 "이름(코드)" 형식 대응
            if ',' in item:
                parts = item.split(',')
                code = parts[0].strip() if parts[0].strip().isdigit() else parts[1].strip()
                name = parts[1].strip() if parts[0].strip().isdigit() else parts[0].strip()
            else:
                code_match = re.search(r'\((\d+)\)', item)
                if code_match:
                    code = code_match.group(1)
                    name = item.split('(')[0]
                else:
                    code = item.strip()
                    name = item

            # 한국 시장 종목 코드는 기본 코스닥(.KQ) 시도 (실패 시 코스피 등 추가 로직 가능)
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
        no_stock_msg = "📉 [필터링 결과] 오늘 조건(느슨한 정배열)에 맞는 종목이 없습니다."
        print(no_stock_msg)
        send_discord_message(no_stock_msg)
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("")
    else:
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(refined_list))
        # 통과된 종목 리스트 전송
        stock_names = ", ".join(refined_list)
        success_msg = f"✨ [필터링 통과] {len(refined_list)}개 종목: {stock_names}"
        send_discord_message(success_msg)
        print(f"✨ 필터링 완료! {len(refined_list)}개 생존.")

if __name__ == "__main__":
    main()
