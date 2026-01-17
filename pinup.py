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
    print("🚀 핀업 테마 정밀 분석 및 리포트 생성 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    report_msg = "📊 **핀업(Finup) 실시간 테마 TOP 5 리포트**\n"
    report_msg += "==========================================\n\n"

    try:
        driver.get("https://finup.co.kr/StockTheme/ThemeMain")
        # 히트맵이나 테마 아이템이 보일 때까지 충분히 기다림
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[class*='item'], [class*='theme']")))
        time.sleep(10)

        # 1. 상위 5개 테마 구역 찾기 (히트맵 내의 각 테마 박스)
        # 사이트 구조에 따라 클래스명이 유동적일 수 있어 여러 패턴 시도
        themes = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")
        if not themes:
            themes = driver.find_elements(By.CSS_SELECTOR, ".item")
            
        themes = themes[:5]
        
        if not themes:
            print("❌ 테마 요소를 찾지 못했습니다. 구조를 다시 확인합니다.")
            return

        for i in range(len(themes)):
            try:
                # 엘리먼트 재참조 (클릭 후 페이지 변화 대비)
                current_themes = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")
                if not current_themes: current_themes = driver.find_elements(By.CSS_SELECTOR, ".item")
                
                target = current_themes[i]
                
                # 테마명과 등락률 수집
                t_name = target.find_element(By.CSS_SELECTOR, ".name").text.strip()
                t_rate = target.find_element(By.CSS_SELECTOR, ".rate").text.strip()
                
                # [핵심] 해당 테마를 클릭하여 하단 종목 리스트 갱신
                driver.execute_script("arguments[0].click();", target)
                time.sleep(3) # 종목 표 로딩 대기
                
                # 하단 상세 종목 리스트에서 상위 5개 추출
                stock_elements = driver.find_elements(By.CSS_SELECTOR, ".stock_list_table .stock_name")[:5]
                stocks = [s.text.strip() for s in stock_elements if s.text.strip()]
                
                report_msg += f"{i+1}위: 🔥 **{t_name}** ({t_rate})\n"
                report_msg += f"└ 종목: {', '.join(stocks) if stocks else '데이터 추출 중...'}\n\n"
                
                print(f"✅ {i+1}위 {t_name} 분석 완료")

            except Exception as e:
                print(f"⚠️ {i+1}위 처리 중 오류: {e}")

        # 디스코드 전송
        report_msg += "==========================================\n"
        report_msg += f"🕒 분석 완료 시각: {time.strftime('%H:%M:%S')}"
        
        requests.post(DISCORD_WEBHOOK_URL, json={"content": report_msg})
        print("🚀 리포트 전송 성공!")

    except Exception as e:
        print(f"❌ 전체 프로세스 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
