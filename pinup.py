import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By  # 에러 해결을 위해 추가
from webdriver_manager.chrome import ChromeDriverManager

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_to_discord(file_path, content):
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            requests.post(DISCORD_WEBHOOK_URL, data={'content': content}, files={'file': f})

def main():
    print("📸 1. 핀업 접속 및 화면 캡처 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,2000')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 1. 주소 접속
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) 

        # 2. 캡처한 화면(body 전체)에서 글씨 추출 및 정렬
        # 맵에 적힌 모든 텍스트를 읽어옵니다.
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        # '이름'과 '%수치'가 붙어있는 패턴을 찾아냅니다.
        # 예: 자동차 부품 +19.15%
        raw_items = re.findall(r'([가-힣A-Za-z0-9/ ]+)\n?([+-]?\d+\.\d+%)', page_text)
        
        extracted = []
        for name, rate in raw_items:
            val = float(rate.replace('%', ''))
            # 너무 긴 텍스트나 노이즈 제거
            if len(name.strip()) < 15:
                extracted.append({'name': name.strip(), 'rate': rate, 'val': val})
        
        # 큰 순서대로 상위 5개 선정
        # 중복 제거 (이름 기준)
        unique_top = {item['name']: item for item in extracted}.values()
        top5 = sorted(unique_top, key=lambda x: x['val'], reverse=True)[:5]

        if not top5:
            print("❌ 화면에서 텍스트를 구분하지 못했습니다. 현재 상태를 캡처합니다.")
            driver.save_screenshot("error_view.png")
            send_to_discord("error_view.png", "❌ 텍스트 추출 실패 - 화면 확인용")
            return

        print(f"✅ 3. TOP 5 감지 성공: {[t['name'] for t in top5]}")

        # 3. 감지된 이름을 하나씩 찾아서 누르고 사진 찍기
        for i, theme in enumerate(top5):
            try:
                t_name = theme['name']
                print(f"🖱️ {i+1}위 클릭: {t_name}")
                
                # 화면에서 해당 글자 요소를 찾아 클릭
                target = driver.find_element(By.XPATH, f"//*[contains(text(), '{t_name}')]")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", target)
                
                time.sleep(8) # 상세 내용 렌더링 대기
                
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(shot_name, f"📊 **{i+1}위: {t_name}** ({theme['rate']})")
                
            except Exception as e:
                print(f"⚠️ {theme['name']} 단계 건너뜀: {e}")

    except Exception as e:
        print(f"❌ 프로세스 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
