import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# 깃허브 시크릿에서 디스코드 주소 가져오기
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def main():
    print("🚀 핀업 실시간 테마 데이터 추출 시작...")
    
    # --- [Step 1] 브라우저 설정 (서버용) ---
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 화면 안 띄움
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # --- [Step 2] 핀업 테마 페이지 접속 ---
        url = "https://finup.co.kr/StockTheme/ThemeMain"
        driver.get(url)
        time.sleep(7) # 페이지 전체 로딩 대기

        # --- [Step 3] TOP 5 테마 찾기 및 순회 ---
        # 핀업은 'theme_item' 또는 'theme_box' 구조를 사용합니다.
        # 화면의 히트맵 영역에서 상위 5개를 가져옵니다.
        theme_elements = driver.find_elements(By.CSS_SELECTOR, ".theme_box")[:5]
        
        if not theme_elements:
            print("❌ 테마 정보를 찾을 수 없습니다. 페이지 구조를 확인해야 합니다.")
            return

        report_msg = "📊 **핀업(Finup) 실시간 테마 TOP 5 리포트**\n"
        report_msg += "==========================================\n\n"

        for i in range(len(theme_elements)):
            # 매 루프마다 엘리먼트를 새로 찾아야 에러가 안 납니다.
            themes = driver.find_elements(By.CSS_SELECTOR, ".theme_box")
            target_theme = themes[i]
            
            # 테마명과 등락률 추출
            theme_name = target_theme.find_element(By.CSS_SELECTOR, ".theme_name").text
            theme_rate = target_theme.find_element(By.CSS_SELECTOR, ".theme_rate").text
            
            # 해당 테마 클릭해서 하단 종목 리스트 갱신
            driver.execute_script("arguments[0].click();", target_theme)
            time.sleep(2) # 종목 리스트 갱 swap 대기
            
            # 하단 종목 리스트 상위 5개 가져오기
            stock_elements = driver.find_elements(By.CSS_SELECTOR, ".stock_list_table tr")[1:6] # 헤더 제외 1~5번
            
            stocks = []
            for stock in stock_elements:
                try:
                    # 종목명 텍스트만 추출
                    name = stock.find_element(By.CSS_SELECTOR, ".stock_name").text
                    stocks.append(name)
                except:
                    continue
            
            # 리포트 문구 작성
            report_msg += f"{i+1}위: 🔥 **{theme_name}** ({theme_rate})\n"
            report_msg += f"└ 종목: {', '.join(stocks) if stocks else '데이터 없음'}\n\n"

        # --- [Step 4] 디스코드 전송 ---
        requests.post(DISCORD_WEBHOOK_URL, json={"content": report_msg})
        print("✅ 테마 데이터 전송 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        # 오류가 나더라도 어디서 났는지 확인하기 위해 디코드에 알림
        # requests.post(DISCORD_WEBHOOK_URL, json={"content": f"⚠️ 핀업 분석 중 오류: {e}"})
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
