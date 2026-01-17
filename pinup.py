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

def send_image_to_discord(file_path, content):
    with open(file_path, 'rb') as f:
        requests.post(DISCORD_WEBHOOK_URL, data={'content': content}, files={'file': f})

def main():
    print("📸 핀업 테마로그 5단계 정밀 클릭 캡처 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1200,1600') # 높이를 좀 더 키움
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) # 초기 로딩을 아주 넉넉하게 줌

        # [방해 요소 제거] 상단 배너나 팝업 등이 클릭을 방해하지 못하도록 삭제
        driver.execute_script("""
            var ads = document.querySelectorAll('.banner, .modal, .popup, [class*="event"]');
            ads.forEach(function(ad) { ad.remove(); });
        """)

        sectors = ["자동차 부품", "정원오", "탈모", "로봇", "제약/바이오"]
        
        for i, name in enumerate(sectors):
            try:
                print(f"🔍 {i+1}순위 '{name}' 섹터 시도 중...")
                
                # 텍스트가 포함된 요소를 더 정밀하게 찾음
                xpath = f"//*[self::div or self::span or self::a][normalize-space()='{name}']"
                target_element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                
                # 화면 중앙 정렬 및 가림 방지
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_element)
                time.sleep(2)

                # 일반 클릭 대신 자바스크립트로 강제 클릭 (배너가 가려도 뚫고 클릭함)
                driver.execute_script("arguments[0].click();", target_element)
                
                # 클릭 후 페이지가 갱신되는 시간을 넉넉히 줌 (핵심!)
                time.sleep(7) 
                
                file_name = f"step_{i+1}_{name.replace('/', '_')}.png"
                driver.save_screenshot(file_name)
                send_image_to_discord(file_name, f"✅ {i+1}단계 캡처 성공: **{name}**")
                
            except Exception as e:
                print(f"⚠️ {name} 클릭 실패: {e}")
                fail_img = f"fail_{i+1}.png"
                driver.save_screenshot(fail_img)
                send_image_to_discord(fail_img, f"❌ {name} 클릭 실패 (방해 요소 확인용 스냅샷)")

    except Exception as e:
        print(f"❌ 전체 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
