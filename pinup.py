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
        
        # [강화 1] 화면 로딩을 위해 최대 20초까지 기다립니다.
        wait = WebDriverWait(driver, 20)
        
        # 팝업창이 있다면 닫기 시도 (방해 요소 제거)
        try:
            driver.execute_script("document.querySelectorAll('.modal').forEach(m => m.style.display='none');")
        except: pass

        # [강화 2] 테마 아이템들이 나타날 때까지 대기
        # 핀업 사이트의 테마 박스들은 '.theme_item_list' 안에 있습니다.
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".item")))
        time.sleep(5) # 추가 안정화 대기

        items = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")[:5]
        
        if not items:
            print("❌ 테마 아이템을 찾지 못했습니다. 구조가 변경되었을 수 있습니다.")
            return

        report_msg = "📊 **핀업(Finup) 실시간 테마 TOP 5 리포트**\n"
        report_msg += "==========================================\n\n"

        for i in range(len(items)):
            try:
                # 엘리먼트 갱신
                current_items = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")
                target = current_items[i]
                
                # 테마명과 등락률 추출
                t_name = target.find_element(By.CSS_SELECTOR, ".name").text.strip()
                t_rate = target.find_element(By.CSS_SELECTOR, ".rate").text.strip()
                
                # 테마 클릭
                driver.execute_script("arguments[0].click();", target)
                time.sleep(3) # 종목 리스트 갱신 대기
                
                # 하단 종목 리스트 테이블에서 종목명 추출
                # '.stock_list_table' 안의 '.stock_name' 클래스를 가진 요소들을 찾습니다.
                stock_elements = driver.find_elements(By.CSS_SELECTOR, ".stock_list_table .stock_name")[:5]
                stocks = [s.text.strip() for s in stock_elements if s.text.strip()]
                
                report_msg += f"{i+1}위: 🔥 **{t_name}** ({t_rate})\n"
                report_msg += f"└ 종목: {', '.join(stocks) if stocks else '종목 정보 로딩 실패'}\n\n"
            except Exception as e:
                print(f"⚠️ {i+1}위 데이터 추출 실패: {e}")

        # 디스코드 전송
        if "🔥" in report_msg:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": report_msg})
            print("✅ 디스코드 전송 완료!")
        else:
            print("❌ 리포트 내용이 비어있습니다.")

    except Exception as e:
        print(f"❌ 전체 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
