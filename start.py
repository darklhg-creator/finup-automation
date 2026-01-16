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
    try:
        # 코스피, 코스닥 전 종목 리스트 가져오기 (가장 안정적인 방식)
        df_krx = fdr.StockListing('KRX')
        
        # 시가총액 상위 300개만 추려서 분석 (속도와 안정성을 위해)
        df_top300 = df_krx.sort_values(by='Marcap', ascending=False).head(300)
        target_codes = df_top300['Code'].tolist()
        target_names = df_top300['Name'].tolist()
        
        result_list = []
        for i, code in enumerate(target_codes):
            try:
                # 최근 30일치 주가 데이터
                df = fdr.DataReader(code, periods=30)
                if len(df) < 20: continue
                
                ma20 = df['Close'].rolling(window=20).mean()
                current_price = df['Close'].iloc[-1]
                current_ma20 = ma20.iloc[-1]
                
                disparity = (current_price / current_ma20) * 100
                
                # 이격도 90 이하인 경우 리스트에 추가
                if disparity <= 90:
                    result_list.append(f"· {target_names[i]}({code}): {disparity:.1f}")
            except:
                continue
        return result_list
    except Exception as e:
        print(f"데이터 수집 중 에러 발생: {e}")
        return []

def main():
    # 1. 종목 분석 실행
    stocks = get_oversold_stocks()
    stock_msg = "\n".join(stocks[:15]) # 최대 15개까지 출력
    
    # 2. 핀업 캡처 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,9000")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(20) # 페이지 로딩 대기
        
        real_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, real_height)
        time.sleep(2)
        
        save_path = "capture.png"
        driver.save_screenshot(save_path)
        
        # 3. 디스코드 전송
        with open(save_path, 'rb') as f:
            content = f"📈 **주식 장 종료 알림** ({datetime.now().strftime('%Y-%m-%d')})\n\n"
            content += "1️⃣ **핀업 테마 로그**\n"
            content += "2️⃣ **이격도 90 이하 우량주 (시총 상위)**\n"
            content += stock_msg if stock_msg else "포착된 종목이 없습니다."
            
            payload = {'content': content}
            files = {'file': ('capture.png', f, 'image/png')}
            requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
            print("전송 완료!")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
