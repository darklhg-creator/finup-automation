import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import os
from datetime import datetime

# 깃허브 금고에서 URL 가져오기
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_to_discord(image_path):
    with open(image_path, 'rb') as f:
        payload = {'content': f"📢 [클라우드 작동] 오늘의 핀업 퇴마록! ({datetime.now().strftime('%Y-%m-%d %H:%M')})"}
        files = {'file': ('capture.png', f, 'image/png')}
        requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files)

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox") # 서버용 필수 설정
    chrome_options.add_argument("--disable-dev-shm-usage") # 서버용 필수 설정
    chrome_options.add_argument("--window-size=1920,9000")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(20) # 서버는 조금 더 느릴 수 있어 20초 대기
        
        real_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, real_height)
        time.sleep(2)
        
        save_path = "capture.png"
        driver.save_screenshot(save_path)
        send_to_discord(save_path)
        print("전송 완료!")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
