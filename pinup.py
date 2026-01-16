import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import os
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_to_discord(image_path):
    with open(image_path, 'rb') as f:
        payload = {'content': f"📢 [클라우드 작동] 오늘의 핀업 퇴마록! ({datetime.now().strftime('%Y-%m-%d %H:%M')})"}
        files = {'file': ('capture.png', f, 'image/png')}
        requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # 화면 없이 실행
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    # 실제 브라우저처럼 보이게 하기 위한 설정
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,2000")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        print("🌐 핀업 페이지 접속 중...")
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        
        # 페이지 로딩 대기 (핀업은 데이터가 많아 충분히 기다려야 합니다)
        time.sleep(15) 
        
        # 전체 화면 캡처를 위해 높이 측정
        real_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, real_height)
        time.sleep(2)
        
        save_path = "capture.png"
        driver.save_screenshot(save_path)
        
        if os.path.exists(save_path):
            send_to_discord(save_path)
            print("🏁 핀업 퇴마록 캡처 및 전송 완료!")
        else:
            print("❌ 캡처 파일 생성 실패")
            
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
