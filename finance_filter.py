import yfinance as yf
import pandas as pd
import os
import re
import requests

# [수정] 보내주신 디스코드 웹훅 주소로 직접 설정합니다.
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def send_discord_message(message):
    if not IGYEOK_WEBHOOK_URL:
        print("⚠️ 디스코드 웹훅 URL이 설정되지 않았습니다.")
        return
    
    payload = {"content": message}
    try:
        response = requests.post(IGYEOK_WEBHOOK_URL, json=payload)
        if response.status_code != 204:
            print(f"⚠️ 디스코드 전송 결과 상태 코드: {response.status_code}")
    except Exception as e:
        print(f"⚠️ 디스코드 전송 실패: {e}")

def check_moving_average_order(ticker):
    try:
        # 이평선 계산을 위해 1년치 데이터 다운로드
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if len(df) < 120:
            return False, None
            
        # 이평선 계산 (20, 60, 120일)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['MA120'] = df['Close'].rolling(window=120).mean()
        
        last_row = df.iloc[-1]
        
        # 1. 중장기 정배열 확인 (60 > 120)
        long_term_trend = last_row['MA60'] > last_row['MA120']
        
        # 2. 60일선 기울기 확인 (최근 5일간 우상향 유지)
        ma60_is_rising = last_row['MA60'] > df['MA60'].iloc[-5]
        
        # 3. 이격도 계산 (20일선 기준)
        disparity = (last_row['Close'] / last_row['MA20']) * 100
        
        # 최종 필터 조건 (느슨한 정배열 + 눌림목 구간)
        if long_term_trend and ma60_is_rising and disparity <= 94.0:
            return True, round(float(disparity), 1)
        return False, None
        
    except Exception as e:
        print(f"⚠️ {ticker} 분석 중 오류: {e}")
        return False, None

def main():
    print("🔍 [느슨한 정배열 필터링] 추세 살아있는 눌림목 선별 중...")
    
    input_file = "targets.txt" 
    
    if not os.path.exists(input_file):
        print(f"❌ '{input_file}' 파일이 없습니다. Step 1이 먼저 실행되어야 합니다.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if not lines:
        print("📝 분석할 종목 리스트가 비어 있습니다.")
        return

    refined_list = []
    print(f"📋 총 {len(lines)}개 종목 기술적 분석 시작...")
    
    for item in lines:
        try:
            # "코드,이름" 또는 "이름(코드)" 형식에서 종목코드 추출
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

            # 코스닥(.KQ) 기준으로 우선 분석
            symbol = f"{code}.KQ"
            is_good, disp_val = check_moving_average_order(symbol)
            
            if is_good:
                refined_list.append(f"{name}({code})")
                print(f"✅ [통과] {name} (이격도: {disp_val}%)")
            else:
                print(f"➖ [탈락] {name}")
        except Exception as e:
            print(f"⚠️ {item} 처리 중 오류 발생: {e}")
            continue

    # 결과 전송 및 파일 업데이트
    if not refined_list:
        no_stock_msg = "📉 [필터링 결과] 오늘 정배열 추세 내 눌림목 조건에 맞는 종목이 없습니다. 관망을 권장합니다. ☕"
        print(no_stock_msg)
        send_discord_message(no_stock_msg)
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("")
    else:
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(refined_list))
        
        stock_names = ", ".join(refined_list)
        success_msg = f"✨ [필터링 성공] {len(refined_list)}개 종목이 기술적 조건을 통과했습니다: {stock_names}"
        send_discord_message(success_msg)
        print(f"✨ 필터링 완료! {len(refined_list)}개 종목 최종 생존.")

if __name__ == "__main__":
    main()
