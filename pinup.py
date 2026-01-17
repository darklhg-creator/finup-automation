import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def send_to_discord(file_path, content):
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            requests.post(DISCORD_WEBHOOK_URL, data={'content': content}, files={'file': f})

def main():
    print("🚀 핀업 화면 기반 텍스트 좌표 클릭 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,1200')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) 

        # 1. TOP 5 리스트 확보 (이미 성공한 로직)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        raw_items = re.findall(r'([가-힣A-Za-z/ ]+)\n?([+-]?\d+\.\d+%)', page_text)
        
        extracted = []
        for name, rate in raw_items:
            val = float(rate.replace('%', ''))
            clean_name = name.strip()
            if len(clean_name) >= 2 and not clean_name.isdigit():
                extracted.append({'name': clean_name, 'rate': rate, 'val': val})
        
        unique_top = {item['name']: item for item in extracted}.values()
        top5 = sorted(unique_top, key=lambda x: x['val'], reverse=True)[:5]

        print(f"✅ 타겟팅 완료: {[t['name'] for t in top5]}")

        # 2. 좌표 기반 클릭 시퀀스
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"🖱️ {i+1}위 클릭 시도: {t_name}")
            
            try:
                # 자바스크립트로 해당 텍스트의 정확한 위치(좌표)를 찾아냅니다.
                find_and_click_script = f"""
                var targetText = "{t_name}";
                var elements = document.querySelectorAll('tspan, div, span');
                for (var el of elements) {{
                    if (el.textContent.trim() === targetText || el.textContent.includes(targetText)) {{
                        var rect = el.getBoundingClientRect();
                        return {{x: rect.left + rect.width/2, y: rect.top + rect.height/2}};
                    }}
                }}
                return null;
                """
                pos = driver.execute_script(find_and_click_script)
                
                if pos:
                    # 마우스 제어를 통해 해당 좌표 클릭
                    actions = ActionChains(driver)
                    actions.move_by_offset(pos['x'], pos['y']).click().perform()
                    # 이동한 마우스 좌표 초기화
                    actions.move_by_offset(-pos['x'], -pos['y']).perform()
                    
                    time.sleep(10) # 상세 화면 로딩
                    
                    shot_name = f"top_{i+1}.png"
                    driver.save_screenshot(shot_name)
                    send_to_discord(shot_name, f"📊 **{i+1}위: {t_name}** ({theme['rate']})")
                    
                    driver.back() # 리스트로 복귀
                    time.sleep(5)
                else:
                    print(f"⚠️ {t_name}의 위치를 화면에서 찾을 수 없습니다.")

            except Exception as e:
                print(f"⚠️ {t_name} 처리 실패: {e}")

    except Exception as e:
        print(f"❌ 프로세스 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
