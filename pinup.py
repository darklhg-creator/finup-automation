import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# 디스코드 웹훅 주소
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def main():
    print("🚀 핀업 실시간 테마 정밀 분석 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    # 사람처럼 보이게 하기 위한 유저 에이전트 추가
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        url = "https://finup.co.kr/StockTheme/ThemeMain"
        driver.get(url)
        time.sleep(10) # 사이트가 무거우니 충분히 대기합니다.

        # 1. 테마 박스들 가져오기 (히트맵 영역)
        # 핀업 사이트 구조: .theme_item_list 내의 .item 들
        themes = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")[:5]
        
        if not themes:
            print("❌ 테마 요소를 찾지 못했습니다. 다른 방식으로 시도합니다.")
            themes = driver.find_elements(By.CSS_SELECTOR, "[class*='theme_item']")[:5]

        report_msg = "📊 **핀업(Finup) 실시간 테마 TOP 5 리포트**\n"
        report_msg += "==========================================\n\n"

        found_data = False
        for i in range(len(themes)):
            try:
                # 루프 돌 때마다 엘리먼트 갱신
                current_themes = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")
                if not current_themes: break
                
                target = current_themes[i]
                
                # 테마명과 등락률 뽑기
                name = target.find_element(By.CSS_SELECTOR, ".name").text
                rate = target.find_element(By.CSS_SELECTOR, ".rate").text
                
                # 테마 클릭해서 하단 종목 리스트 띄우기
                driver.execute_script("arguments[0].click();", target)
                time.sleep(2)
                
                # 하단 종목 리스트 (테이블 내 종목명 추출)
                # 핀업 하단 테이블의 종목명 클래스는 보통 .stock_name 입니다.
                stock_rows = driver.find_elements(By.CSS_SELECTOR, ".stock_list_table tr")[1:6]
                
                stocks = []
                for row in stock_rows:
                    try:
                        stock_name = row.find_element(By.CSS_SELECTOR, ".stock_name").text
                        if stock_name: stocks.append(stock_name)
                    except: continue
                
                report_msg += f"{i+1}위: 🔥 **{name}** ({rate})\n"
                report_msg += f"└ 종목: {', '.join(stocks) if stocks else '종목 정보 없음'}\n\n"
                found_data = True
            except Exception as e:
                print(f"⚠️ {i+1}위 테마 처리 중 오류: {e}")
                continue

        if found_data:
            # 디스코드 전송
            requests.post(DISCORD_WEBHOOK_URL, json={"content": report_msg})
            print("✅ 디스코드 전송 완료!")
        else:
            print("❌ 추출된 데이터가 없어 메시지를 보내지 않았습니다.")

    except Exception as e:
        print(f"❌ 전체 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
