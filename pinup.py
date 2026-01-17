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
    """디스코드에 텍스트와 이미지를 함께 전송합니다."""
    with open(file_path, 'rb') as f:
        requests.post(DISCORD_WEBHOOK_URL, data={'content': content}, files={'file': f})

def main():
    print("📸 핀업 테마로그 5단계 클릭 캡처 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1200,1400') # 리스트가 길 수 있어 높이를 키움
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    try:
        # 1. 테마로그 주소 접속
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(10) # 페이지 안정화 대기

        # 2. 상위 5개 섹터 클릭 및 캡처 루프
        # 테마로그 페이지의 각 섹터 클릭 요소 찾기
        # 보통 .theme-name 또는 특정 텍스트를 포함한 셀(td)을 타겟팅합니다.
        sectors = ["자동차 부품", "정원오", "탈모", "로봇", "제약/바이오"]
        
        for i, name in enumerate(sectors):
            try:
                print(f"🔍 {i+1}순위 '{name}' 섹터 찾는 중...")
                
                # 텍스트로 해당 섹션 찾기 (가장 확실한 방법)
                target_xpath = f"//div[contains(text(), '{name}')] | //span[contains(text(), '{name}')] | //a[contains(text(), '{name}')]"
                target_element = wait.until(EC.element_to_be_clickable((By.XPATH, target_xpath)))
                
                # 화면 중앙으로 스크롤 후 클릭
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_element)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", target_element)
                
                time.sleep(5) # 종목 리스트 갱신 대기
                
                # 캡처 및 저장
                file_name = f"step_{i+1}_{name.replace('/', '_')}.png"
                driver.save_screenshot(file_name)
                
                # 디스코드 전송
                send_image_to_discord(file_name, f"✅ {i+1}단계 캡처 완료: **{name}**")
                print(f"📸 {name} 캡처 및 전송 완료")
                
            except Exception as e:
                print(f"⚠️ {name} 처리 중 오류: {e}")
                # 오류 시 현재 화면이라도 찍어서 전송 (원인 파악용)
                driver.save_screenshot(f"error_{i+1}.png")
                send_image_to_discord(f"error_{i+1}.png", f"❌ {name} 클릭 실패 (현재 화면 스크린샷)")

    except Exception as e:
        print(f"❌ 전체 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
