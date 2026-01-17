import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_to_discord(file_path, content):
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            requests.post(DISCORD_WEBHOOK_URL, data={'content': content}, files={'file': f})

def main():
    print("📸 1. 핀업 접속 및 TOP 5 리스트 확보...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,2000')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) 

        # 1. 화면 텍스트에서 순수 테마명만 추출 (숫자 노이즈 제거)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        raw_items = re.findall(r'([가-힣A-Za-z/ ]+)\n?([+-]?\d+\.\d+%)', page_text)
        
        extracted = []
        for name, rate in raw_items:
            val = float(rate.replace('%', ''))
            clean_name = name.strip()
            # 2글자 미만이나 숫자로만 된 노이즈 필터링
            if len(clean_name) >= 2 and not clean_name.isdigit():
                extracted.append({'name': clean_name, 'rate': rate, 'val': val})
        
        # 중복 제거 후 상위 5개 선정
        unique_top = {item['name']: item for item in extracted}.values()
        top5 = sorted(unique_top, key=lambda x: x['val'], reverse=True)[:5]

        if not top5:
            print("❌ 테마 리스트 확보 실패")
            return

        print(f"✅ 감지된 TOP 5: {[t['name'] for t in top5]}")

        # 2. 각 테마를 클릭하며 캡처 (Stale 에러 방지 로직)
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"🖱️ {i+1}위 클릭 시도: {t_name}")
            
            try:
                # [중요] 클릭 직전에 요소를 매번 새로 찾음 (에러 방지 핵심)
                target = driver.find_element(By.XPATH, f"//*[text()='{t_name}' or contains(text(), '{t_name}')]")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", target)
                
                # 상세 종목 화면 렌더링 대기
                time.sleep(10)
                
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(shot_name, f"📊 **{i+1}위: {t_name}** ({theme['rate']})")
                
                # 리스트 화면으로 복귀 (뒤로 가기)
                driver.back()
                time.sleep(5) 
                
            except Exception as e:
                print(f"⚠️ {t_name} 클릭 오류 (재시도): {e}")
                # 클릭 실패 시 다른 방식으로 재시도하거나 기록
                continue

    except Exception as e:
        print(f"❌ 프로세스 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
