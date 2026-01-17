import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_image_to_discord(file_path, content):
    with open(file_path, 'rb') as f:
        requests.post(DISCORD_WEBHOOK_URL, data={'content': content}, files={'file': f})

def main():
    print("🚀 핀업 히트맵 상위 5개 섹터 자동 감지 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1400,1600')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 25)
    
    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) # 전체 로딩 대기

        # 1. 모든 테마 아이템 수집
        # 핀업 테마로그의 각 박스 요소들을 가져옵니다.
        items = driver.find_elements(By.CSS_SELECTOR, ".item, [class*='ThemeItem']")
        
        theme_data = []
        for item in items:
            try:
                name = item.find_element(By.CSS_SELECTOR, ".name").text.strip()
                rate_str = item.find_element(By.CSS_SELECTOR, ".rate").text.strip()
                # '+15.2%' 등에서 숫자만 추출하여 정렬 기준으로 사용
                rate_val = float(re.sub(r'[^0-9.-]', '', rate_str))
                theme_data.append({'element': item, 'name': name, 'rate': rate_str, 'val': rate_val})
            except:
                continue

        # 2. 등락률(% 수치) 높은 순으로 상위 5개 정렬
        top5 = sorted(theme_data, key=lambda x: x['val'], reverse=True)[:5]
        
        if not top5:
            print("❌ 상위 섹터를 추출하지 못했습니다. 화면 구성을 다시 확인합니다.")
            driver.save_screenshot("debug_main.png")
            send_image_to_discord("debug_main.png", "❌ 데이터 추출 실패 당시 화면")
            return

        print(f"✅ 감지된 상위 5개: {[t['name'] for t in top5]}")

        # 3. 상위 5개 순차 클릭 및 캡처
        for i, theme in enumerate(top5):
            try:
                print(f"📸 {i+1}위 클릭 중: {theme['name']} ({theme['rate']})")
                
                # 가림 현상 방지를 위해 해당 요소로 스크롤
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", theme['element'])
                time.sleep(2)
                
                # 자바스크립트로 직접 클릭 (안정적임)
                driver.execute_script("arguments[0].click();", theme['element'])
                time.sleep(7) # 하단 종목 리스트 렌더링 대기
                
                file_name = f"top_{i+1}.png"
                driver.save_screenshot(file_name)
                
                send_image_to_discord(file_name, f"🔥 **{i+1}위: {theme['name']}** ({theme['rate']})")
                
            except Exception as e:
                print(f"⚠️ {theme['name']} 캡처 실패: {e}")

    except Exception as e:
        print(f"❌ 전체 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
