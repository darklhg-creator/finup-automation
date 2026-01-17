import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def main():
    print("📱 핀업 모바일 모드 위장 접속 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # [핵심] 모바일 기기(아이폰)처럼 보이게 설정
    user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument('--window-size=375,812') # 아이폰 크기
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 모바일 테마 메인 접속
        url = "https://finup.co.kr/StockTheme/ThemeMain"
        driver.get(url)
        time.sleep(10) # 모바일 화면 로딩 대기

        # 모바일 버전에서는 테마 항목들이 보통 .item 또는 .theme_item_list 내부에 있습니다.
        items = driver.find_elements(By.CSS_SELECTOR, ".item")[:5]
        
        if not items:
            print("❌ 모바일 화면에서도 데이터를 찾지 못했습니다.")
            return

        report_msg = "📊 **핀업(Finup) 모바일 실시간 테마 TOP 5**\n"
        report_msg += "==========================================\n\n"

        for i in range(len(items)):
            try:
                # 엘리먼트 갱신
                curr_items = driver.find_elements(By.CSS_SELECTOR, ".item")
                target = curr_items[i]
                
                # 텍스트 추출 (모바일은 구조가 더 단순함)
                name = target.find_element(By.CSS_SELECTOR, ".name").text.strip()
                rate = target.find_element(By.CSS_SELECTOR, ".rate").text.strip()
                
                # 테마 클릭하여 종목 리스트 확인
                driver.execute_script("arguments[0].click();", target)
                time.sleep(3)
                
                # 종목명 추출 (모바일 리스트 클래스)
                stock_elements = driver.find_elements(By.CSS_SELECTOR, ".stock_name")[:5]
                stocks = [s.text.strip() for s in stock_elements if s.text.strip()]
                
                report_msg += f"{i+1}위: 🔥 **{name}** ({rate})\n"
                report_msg += f"└ 종목: {', '.join(stocks) if stocks else '조회 중...'}\n\n"
            except:
                continue

        if "🔥" in report_msg:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": report_msg})
            print("✅ 핀업 모바일 데이터 전송 완료!")
        else:
            print("❌ 추출된 데이터가 없습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
