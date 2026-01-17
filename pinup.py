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
    print("🚀 핀업 실시간 테마 정밀 분석 (봇 방어 우회 모드) 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # [우회 설정 1] 진짜 사람처럼 보이는 유저 에이전트와 옵션들
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # [우회 설정 2] 웹드라이버 감지 방지 스크립트
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    try:
        url = "https://finup.co.kr/StockTheme/ThemeMain"
        driver.get(url)
        
        # [데이터 대기] 테마 요소가 뜰 때까지 충분히 대기 (최대 30초)
        wait = WebDriverWait(driver, 30)
        
        # 테마 리스트가 나타날 때까지 기다림
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".item, .theme_box")))
        except:
            print("❌ 로딩 시간이 초과되었습니다. 페이지 스냅샷을 분석합니다.")

        time.sleep(7) # 안정화 대기

        # 1. 테마 박스 찾기 (여러 선택자를 동시에 시도)
        items = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")
        if not items:
            items = driver.find_elements(By.CSS_SELECTOR, ".item")
            
        if not items:
            print("❌ 데이터를 찾지 못했습니다. 사이트 구조가 방어 중일 수 있습니다.")
            return

        report_msg = "📊 **핀업(Finup) 실시간 테마 TOP 5 리포트**\n"
        report_msg += "==========================================\n\n"

        found_count = 0
        for i in range(len(items)):
            if found_count >= 5: break
            try:
                # 엘리먼트 갱신
                curr_items = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")
                if not curr_items: curr_items = driver.find_elements(By.CSS_SELECTOR, ".item")
                
                target = curr_items[i]
                
                # 테마명과 등락률 추출
                try:
                    t_name = target.find_element(By.CSS_SELECTOR, ".name").text.strip()
                    t_rate = target.find_element(By.CSS_SELECTOR, ".rate").text.strip()
                except: continue

                if not t_name: continue

                # 테마 클릭
                driver.execute_script("arguments[0].click();", target)
                time.sleep(3)
                
                # 하단 종목 추출
                stock_elements = driver.find_elements(By.CSS_SELECTOR, ".stock_list_table .stock_name")[:5]
                stocks = [s.text.strip() for s in stock_elements if s.text.strip()]
                
                report_msg += f"{found_count+1}위: 🔥 **{t_name}** ({t_rate})\n"
                report_msg += f"└ 종목: {', '.join(stocks) if stocks else '조회 중...'}\n\n"
                found_count += 1
            except:
                continue

        if found_count > 0:
            requests.post(DISCORD_WEBHOOK_URL, json={"content": report_msg})
            print(f"✅ {found_count}개 테마 전송 완료!")
        else:
            print("❌ 추출된 유효 데이터가 없습니다.")

    except Exception as e:
        print(f"❌ 최종 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
