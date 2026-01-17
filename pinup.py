import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def main():
    print("🚀 핀업 테마로그(ThemeLog) 정밀 분석 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    report_msg = "📊 **핀업(Finup) 테마로그 TOP 5 리포트**\n"
    report_msg += "==========================================\n\n"

    try:
        # 알려주신 정확한 주소로 접속
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        
        # 테마 리스트가 나타날 때까지 대기
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".theme-list, .list-item, tr")))
        time.sleep(7) # 데이터 렌더링을 위한 추가 시간

        # 1. 상위 5개 테마 행(Row) 찾기
        # 핀업 테마로그의 리스트 구조를 타겟팅합니다.
        themes = driver.find_elements(By.CSS_SELECTOR, ".list-item")[:5]
        
        if not themes:
            # 다른 클래스명 시도 (사이트 구조 대응)
            themes = driver.find_elements(By.CSS_SELECTOR, "table tr")[1:6]

        if not themes:
            print("❌ 테마로그 리스트를 찾지 못했습니다.")
            return

        for i in range(len(themes)):
            try:
                # 엘리먼트 갱신
                current_themes = driver.find_elements(By.CSS_SELECTOR, ".list-item")
                if not current_themes: current_themes = driver.find_elements(By.CSS_SELECTOR, "table tr")[1:6]
                
                target = current_themes[i]
                
                # 테마명과 등락률 수집
                t_name = target.find_element(By.CSS_SELECTOR, ".theme-name, .name").text.strip()
                t_rate = target.find_element(By.CSS_SELECTOR, ".percent, .rate").text.strip()
                
                # 2. 테마 클릭 (상세 종목을 보기 위함)
                driver.execute_script("arguments[0].click();", target)
                time.sleep(3)
                
                # 3. 상세 종목 5개 수집
                # 핀업 상세 페이지의 종목명 클래스를 찾습니다.
                stock_elements = driver.find_elements(By.CSS_SELECTOR, ".stock-name, .name")[:5]
                stocks = [s.text.strip() for s in stock_elements if s.text.strip() and s.text.strip() != t_name]
                
                report_msg += f"{i+1}위: 🔥 **{t_name}** ({t_rate})\n"
                report_msg += f"└ 종목: {', '.join(stocks[:5]) if stocks else '종목 확인 중...'}\n\n"
                
                print(f"✅ {i+1}위 {t_name} 완료")
                
                # 다시 리스트로 돌아가기 (필요한 경우)
                driver.back()
                time.sleep(3)

            except Exception as e:
                print(f"⚠️ {i+1}위 처리 중 오류: {e}")

        # 디스코드 전송
        report_msg += "==========================================\n"
        requests.post(DISCORD_WEBHOOK_URL, json={"content": report_msg})
        print("🚀 리포트 전송
