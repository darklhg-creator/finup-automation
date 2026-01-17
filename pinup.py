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
    print("🚀 핀업 테마로그 수치 상위 5개 섹터 정밀 추적 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1400,2000') # 캡처 영역 확보를 위해 높이 증가
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 25)
    
    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) # 전체 데이터 로딩 대기

        # 1. 화면의 모든 테마 박스 수집
        items = driver.find_elements(By.CSS_SELECTOR, ".item, [class*='ThemeItem']")
        
        theme_list = []
        for item in items:
            try:
                name = item.find_element(By.CSS_SELECTOR, ".name").text.strip()
                rate_text = item.find_element(By.CSS_SELECTOR, ".rate").text.strip()
                
                # 수치 추출 (예: "+15.2%" -> 15.2)
                val = float(re.sub(r'[^0-9.-]', '', rate_text))
                
                theme_list.append({
                    'element': item, 
                    'name': name, 
                    'rate': rate_text, 
                    'val': val 
                })
            except:
                continue

        # 2. 수치(val)가 높은 순서대로 상위 5개 정렬 (단순 내림차순)
        top5 = sorted(theme_list, key=lambda x: x['val'], reverse=True)[:5]
        
        if not top5:
            print("❌ 상위 섹터 데이터를 추출하지 못했습니다.")
            return

        print(f"📊 타겟팅된 상위 5개 섹터: {[t['name'] for t in top5]}")

        # 3. 상위 5개 순차 클릭 및 캡처
        for i, theme in enumerate(top5):
            try:
                print(f"📸 {i+1}위 캡처 중: {theme['name']} ({theme['rate']})")
                
                # 가림 방지를 위해 중앙 정렬
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", theme['element'])
                time.sleep(2)
                
                # 강제 클릭 (JS 방식이 가장 확실함)
                driver.execute_script("arguments[0].click();", theme['element'])
                
                # 하단 종목 리스트가 완전히 바뀔 때까지 넉넉히 대기
                time.sleep(10) 
                
                file_name = f"top_{i+1}.png"
                driver.save_screenshot(file_name)
                
                # 디코 전송
                send_image_to_discord(file_name, f"✅ **{i+1}위: {theme['name']}** ({theme['rate']})")
                
            except Exception as e:
                print(f"⚠️ {theme['name']} 처리 중 오류: {e}")

    except Exception as e:
        print(f"❌ 전체 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
