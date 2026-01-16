Python

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
    # 코스피 200, 코스닥 150 분석
    ks200 = fdr.StockListing('KOSPI 200')['Code']
    kq150 = fdr.StockListing('KOSDAQ 150')['Code']
    target_codes = pd.concat([ks200, kq150]).unique()
    
    result_list = []
    for code in target_codes:
        try:
            df = fdr.DataReader(code, periods=30)
            if len(df) < 20: continue
            ma20 = df['Close'].rolling(window=20).mean()
            current_price = df['Close'].iloc[-1]
            current_ma20 = ma20.iloc[-1]
            disparity = (current_price / current_ma20) * 100
            if disparity <= 90:
                result_list.append(f"· {code} (이격도: {disparity:.1f})")
        except: continue
    return result_list

def main():
    stocks = get_oversold_stocks()
    stock_msg = "\n".join(stocks[:10])
    
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
        
        # 통합 전송
        with open(save_path, 'rb') as f:
            content = f"📈 **주식 장 종료 알림**\n\n1️⃣ **핀업 캡처**\n2️⃣ **이격도 90 이하 우량주**\n{stock_msg if stock_msg else '포착 종목 없음'}"
            payload = {'content': content}
            files = {'file': ('capture.png', f, 'image/png')}
            requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
