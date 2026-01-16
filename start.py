import requests
import FinanceDataReader as fdr
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import os
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_oversold_stocks():
    print("우량주 이격도 분석 시작 (범위: 시총 상위 500위)...")
    try:
        # 1. 시가총액 상위 500개 종목 가져오기
        df_krx = fdr.StockListing('KRX')
        df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
        target_codes = df_top500['Code'].tolist()
        target_names = df_top500['Name'].tolist()
        
        all_stocks_data = [] # 모든 분석 데이터를 임시 저장
        
        for i, code in enumerate(target_codes):
            try:
                df = fdr.DataReader(code, periods=30)
                if len(df) < 20: continue
                
                ma20 = df['Close'].rolling(window=20).mean()
                current_price = df['Close'].iloc[-1]
                current_ma20 = ma20.iloc[-1]
                disparity = (current_price / current_ma20) * 100
                
                all_stocks_data.append({
                    'name': target_names[i],
                    'code': code,
                    'disparity': disparity
                })
            except:
                continue
        
        # 2. 필터링 로직 (90 이하 먼저 찾기)
        under_90 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data if s['disparity'] <= 90]
        
        if under_90:
            return "🎯 [1차 필터: 이격도 90 이하 포착]", under_90
        else:
            # 90 이하가 없으면 95 이하 찾기
            under_95 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data if s['disparity'] <= 95]
            return "🔍 [2차 필터: 이격도 95 이하 검색 결과]", under_95

    except Exception as e:
        print(f"데이터 분석 중 에러: {e}")
        return "⚠️ 분석 중 에러 발생", []

def main():
    # 1. 단계별 종목 분석
    title_text, stocks = get_oversold_stocks()
    stock_msg = "\n".join(stocks[:20]) # 최대 20개까지 출력
    
    # 2. 핀업 캡처 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,9000")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(20)
        
        real_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, real_height)
        time.sleep(2)
        
        save_path = "capture.png"
        driver.save_screenshot(save_path)
        
        # 3. 디스코드 전송
        with open(save_path, 'rb') as f:
            content = f"📈 **주식 장 종료 보고서** ({datetime.now().strftime('%Y-%m-%d')})\n\n"
            content += f"**{title_text}**\n"
            content += stock_msg if stock_msg else "조건에 맞는 종목이 없습니다."
            content += "\n\n**3️⃣ 핀업 테마 로그 (아래 이미지)**"
            
            payload = {'content': content}
            files = {'file': ('capture.png', f, 'image/png')}
            requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
            print("전송 완료!")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
