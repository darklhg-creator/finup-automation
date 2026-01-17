import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_to_discord_with_image(file_path, content):
    """디스코드에 텍스트와 이미지를 함께 보냅니다."""
    with open(file_path, 'rb') as f:
        payload = {'content': content}
        files = {'file': f}
        requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)

def main():
    print("📸 핀업 테마 TOP 5 이미지 캡처 분석 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1200,1000')
    # 유저 에이전트 추가로 차단 방지
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        url = "https://finup.co.kr/StockTheme/ThemeMain"
        driver.get(url)
        time.sleep(10) # 페이지 전체 로딩 대기

        # 1. 상위 테마 5개 요소 찾기
        items = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")[:5]
        
        if not items:
            print("❌ 테마 요소를 찾지 못했습니다.")
            return

        for i in range(len(items)):
            try:
                # 루프마다 엘리먼트 갱신 (클릭 후 DOM 변화 대비)
                current_items = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")
                target = current_items[i]
                
                # 테마명 추출
                t_name = target.find_element(By.CSS_SELECTOR, ".name").text.strip()
                t_rate = target.find_element(By.CSS_SELECTOR, ".rate").text.strip()
                
                # 해당 테마 클릭 (하위 종목 리스트 갱신)
                driver.execute_script("arguments[0].click();", target)
                time.sleep(3) # 하단 종목 테이블 로딩 대기
                
                # 캡처 저장
                file_name = f"top{i+1}.png"
                driver.save_screenshot(file_name)
                print(f"✅ {i+1}위 테마({t_name}) 캡처 완료")
                
                # 디코로 이미지 전송
                msg = f"📊 **핀업 테마 {i+1}위**: {t_name} ({t_rate})"
                send_to_discord_with_image(file_name, msg)
                
            except Exception as e:
                print(f"⚠️ {i+1}위 처리 중 오류: {e}")

    except Exception as e:
        print(f"❌ 전체 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
