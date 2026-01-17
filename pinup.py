import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def main():
    print("🚀 핀업 실시간 테마 정밀 분석 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        url = "https://finup.co.kr/StockTheme/ThemeMain"
        driver.get(url)
        time.sleep(15) # 로딩 시간을 아주 넉넉히 잡습니다 (데이터가 늦게 뜰 수 있음)

        # 핀업 메인 히트맵에서 상위 5개 아이템 추출
        # CSS 선택자를 더 범용적인 것으로 변경
        items = driver.find_elements(By.CLASS_NAME, "item")[:5]
        
        if not items:
            print("❌ 데이터를 찾지 못했습니다. 클래스명을 재검토합니다.")
            return

        report_msg = "📊 **핀업(Finup) 실시간 테마 TOP 5 리포트**\n"
        report_msg += "==========================================\n\n"

        for i in range(len(items)):
            try:
                # 엘리먼트 재참조
                current_items = driver.find_elements(By.CLASS_NAME, "item")
                target = current_items[i]
                
                t_name = target.find_element(By.CLASS_NAME, "name").text
                t_rate = target.find_element(By.CLASS_NAME, "rate").text
                
                # 해당 테마 클릭
                driver.execute_script("arguments[0].click();", target)
                time.sleep(3)
                
                # 종목 리스트 추출 (테이블 행들)
                rows = driver.find_elements(By.CSS_SELECTOR, ".stock_list_table tr")[1:6]
                stocks = []
                for r in rows:
                    try:
                        s_name = r.find_element(By.CLASS_NAME, "stock_name").text
                        if s_name: stocks.append(s_name)
                    except: continue
                
                report_msg += f"{i+1}위: 🔥 **{t_name}** ({t_rate})\n"
                report_msg += f"└ 종목: {', '.join(stocks) if stocks else '데이터 없음'}\n\n"
            except Exception as e:
                print(f"⚠️ {i+1}위 처리 실패: {e}")

        # 디스코드 전송
        if "🔥" in report_msg:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": report_msg})
            print("✅ 전송 완료")
        else:
            print("❌ 보낼 데이터가 없습니다.")

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
