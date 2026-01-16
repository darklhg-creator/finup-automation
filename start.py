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
    print("우량주 이격도 분석 시작 (범위: 시총 상위 1,000위)...")
    try:
        # 1. 시가총액 상위 1,000개 종목 가져오기
        df_krx = fdr.StockListing('KRX')
        df_top1000 = df_krx.sort_values(by='Marcap', ascending=False).head(1000)
        target_codes = df_top1000['Code'].tolist()
        target_names = df_top1000['Name'].tolist()
        
        all_stocks_data = []
        
        for i, code in enumerate(target_codes):
            try:
                # 데이터 수집 (최근 30일치)
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
        
        # 2. 계층형 필터링 로직
        # 1순위: 이격도 90 이하
        under_90 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data if s['disparity'] <= 90]
        
        if under_90:
            return "🎯 [1차 필터: 이격도 90 이하 포착]", under_90
        else:
            # 2순위: 90 이하가 없으면 95 이하 검색
            under_95 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data if s['disparity'] <= 95]
            return "🔍 [2차 필터: 이격도 95 이하 검색 결과]", under_95

    except Exception as e:
        print(f"데이터 분석 중 에러: {e}")
        return "⚠️ 분석 중 에러 발생", []

def main():
    # 1. 종목 분석
    title_text, stocks = get_oversold_stocks()
    stock_msg = "\n".join(stocks[:25]) # 종목이 많을 수 있으니 최대 25개까지 표시
    
    # 2. 핀업 캡처
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
        
        # 3. 디스코드 통합 전송
        with open(save_path, 'rb') as f:
            content = f"📈 **주식 장 종료 보고서** ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
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
