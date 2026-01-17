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
    print("🔍 통합 시총 상위 500위 분석 시작 (코스피/코스닥 포함)...")
    try:
        # 시장 구분 없이 통합 시총 상위 500개 추출
        df_krx = fdr.StockListing('KRX')
        df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
        target_codes = df_top500['Code'].tolist()
        target_names = df_top500['Name'].tolist()
        
        all_stocks_data = []
        
        for i, code in enumerate(target_codes):
            try:
                # 최근 25일치 데이터만 가져와서 속도 최적화 ⚡
                df = fdr.DataReader(code).tail(25)
                if len(df) < 20: continue
                
                # 이격도 계산
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                disparity = (current_price / ma20) * 100
                
                all_stocks_data.append({'name': target_names[i], 'code': code, 'disparity': disparity})
                
                # 100개마다 진행 상황 출력
                if (i + 1) % 100 == 0: print(f"✅ {i+1}/500 종목 분석 완료")
            except:
                continue
        
        # 필터링 및 결과 정리
        all_stocks_data.sort(key=lambda x: x['disparity'])
        under_95 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data if s['disparity'] <= 95]
        
        if under_95:
            return "🔍 [이격도 95 이하 포착]", under_95
        
        lowest_5 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data[:5]]
        return "❓ [이격도 최하위 5종목]", lowest_5

    except Exception as e:
        print(f"❌ 데이터 에러: {e}")
        return "⚠️ 분석 중 오류 발생", []

def main():
    title_text, stocks = get_oversold_stocks()
    stock_msg = "\n".join(stocks[:25])
    
    print("📸 핀업 테마 로그 캡처 시작...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(12) # 페이지 로딩 대기
        save_path = "capture.png"
        driver.save_screenshot(save_path)
        
        with open(save_path, 'rb') as f:
            content = f"📈 **주식 장 종료 보고서**\n\n**{title_text}**\n{stock_msg}\n\n**3️⃣ 핀업 테마 로그**"
            requests.post(DISCORD_WEBHOOK_URL, data={'content': content}, files={'file': f})
            print("🏁 모든 작업 성공 및 디스코드 전송 완료!")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
