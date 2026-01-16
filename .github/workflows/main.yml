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
    print("우량주 이격도 분석 시작...")
    # 코스피 200, 코스닥 150 종목 리스트 합치기
    ks200 = fdr.StockListing('KOSPI 200')['Code']
    kq150 = fdr.StockListing('KOSDAQ 150')['Code']
    target_codes = pd.concat([ks200, kq150]).unique()
    
    result_list = []
    
    # 분석 기준일 (오늘)
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    for code in target_codes:
        try:
            # 최근 40일치 데이터 가져오기
            df = fdr.DataReader(code, periods=40)
            if len(df) < 20: continue
            
            # 20일 이동평균선 계산
            ma20 = df['Close'].rolling(window=20).mean()
            current_price = df['Close'].iloc[-1]
            current_ma20 = ma20.iloc[-1]
            
            # 이격도 계산
            disparity = (current_price / current_ma20) * 100
            
            # 조건: 이격도 90 이하
            if disparity <= 90:
                name = fdr.DataReader(code, periods=1)['Name'].iloc[0] if 'Name' not in df.columns else ""
                # 이름이 안나올 경우를 대비해 시세표에서 가져오기 (간소화)
                result_list.append(f"· {code} (이격도: {disparity:.1f})")
        except:
            continue
            
    return result_list

def send_to_discord(image_path, stock_msg):
    with open(image_path, 'rb') as f:
        content = f"📈 **주식 장 종료 알림** ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        content += "1️⃣ **핀업 퇴마록 캡처** (아래 이미지 참고)\n"
        content += "2️⃣ **이격도 90 이하 우량주 포착**\n"
        content += stock_msg if stock_msg else "포착된 종목이 없습니다."
        
        payload = {'content': content}
        files = {'file': ('capture.png', f, 'image/png')}
        requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)

def main():
    # 1. 종목 분석
    stocks = get_oversold_stocks()
    stock_msg = "\n".join(stocks[:10]) # 너무 많으면 상위 10개만
    
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
        
        # 3. 통합 전송
        send_to_discord(save_path, stock_msg)
        print("전송 완료!")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
