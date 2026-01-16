import requests
import FinanceDataReader as fdr
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import os
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_oversold_stocks():
    now = datetime.now()
    start_date = (now - timedelta(days=60)).strftime('%Y-%m-%d')
    end_date = now.strftime('%Y-%m-%d')
    
    # 700위로 범위를 조정하여 속도를 높였습니다 🚀
    print(f"[{end_date}] 시총 상위 700위 분석 시작...")
    
    try:
        df_krx = fdr.StockListing('KRX')
        df_top700 = df_krx.sort_values(by='Marcap', ascending=False).head(700)
        target_codes = df_top700['Code'].tolist()
        target_names = df_top700['Name'].tolist()
        
        all_stocks_data = []
        
        for i, code in enumerate(target_codes):
            try:
                df = fdr.DataReader(code, start=start_date, end=end_date)
                if len(df) < 20: continue
                
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                disparity = (current_price / ma20) * 100
                
                all_stocks_data.append({'name': target_names[i], 'code': code, 'disparity': disparity})
                
                # 100개마다 진행 상황을 로그에 찍어줍니다 📝
                if i % 100 == 0: print(f"분석 중... {i}/700")
            except:
                continue
        
        # 필터링 로직
        under_90 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data if s['disparity'] <= 90]
        if under_90:
            return "🎯 [이격도 90 이하 포착]", under_90
            
        under_95 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data if s['disparity'] <= 95]
        if under_95:
            return "🔍 [이격도 95 이하 결과]", under_95
            
        # 아무것도 없을 때를 대비한 최하위 5개 출력
        all_stocks_data.sort(key=lambda x: x['disparity'])
        lowest_5 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data[:5]]
        return "❓ [이격도 최하위 5종목]", lowest_5

    except Exception as e:
        print(f"데이터 에러: {e}")
        return "⚠️ 분석 에러", []

def main():
    title_text, stocks = get_oversold_stocks()
    stock_msg = "\n".join(stocks[:25])
    
    print("핀업 캡처 시작...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,2000")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) # 페이지 로딩 대기
        
        save_path = "capture.png"
        driver.save_screenshot(save_path)
        
        with open(save_path, 'rb') as f:
            content = f"📈 **주식 장 종료 보고서** ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n**{title_text}**\n{stock_msg}\n\n**3️⃣ 핀업 테마 로그**"
            payload = {'content': content}
            files = {'file': ('capture.png', f, 'image/png')}
            requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)
            print("전송 완료!")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
