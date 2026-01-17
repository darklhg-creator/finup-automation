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
    print("🚀 핀업 스크롤 보정 및 정밀 좌표 클릭 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # 화면 높이를 넉넉히 2500으로 설정하여 모든 섹터가 한 번에 보이게 함
    chrome_options.add_argument('--window-size=1600,2500')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) 

        # 1. TOP 5 리스트 확보
        page_text = driver.find_element(By.TAG_NAME, "body").text
        raw_items = re.findall(r'([가-힣A-Za-z/ ]{2,})\n?([+-]?\d+\.\d+%)', page_text)
        
        extracted = []
        for name, rate in raw_items:
            val = float(rate.replace('%', ''))
            clean_name = name.strip()
            if not clean_name.isdigit() and len(clean_name) < 15:
                extracted.append({'name': clean_name, 'rate': rate, 'val': val})
        
        unique_top = {item['name']: item for item in extracted}.values()
        top5 = sorted(unique_top, key=lambda x: x['val'], reverse=True)[:5]

        print(f"✅ 타겟팅 리스트: {[t['name'] for t in top5]}")

        # 2. 좌표 클릭 시퀀스 (스크롤 보정 포함)
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"🔍 {i+1}위 추적: {t_name}")
            
            # 요소 찾기 및 스크롤 스크립트
            find_and_scroll_script = f"""
            var target = "{t_name}";
            var els = document.querySelectorAll('tspan, text, div, span');
            for (var el of els) {{
                if (el.textContent.includes(target)) {{
                    el.scrollIntoView({{block: "center", inline: "center"}});
                    var r = el.getBoundingClientRect();
                    return {{x: r.left + r.width/2, y: r.top + r.height/2}};
                }}
            }}
            return null;
            """
            pos = driver.execute_script(find_and_scroll_script)
            time.sleep(2) # 스크롤 후 안정화 대기

            if pos:
                print(f"🎯 좌표 확인 (스크롤 완료): ({pos['x']}, {pos['y']})")
                try:
                    # 이제 화면 중앙에 있으므로 클릭이 가능함
                    actions = ActionChains(driver)
                    # 스크롤된 상태에서의 뷰포트 좌표를 직접 클릭
                    driver.execute_script(f"document.elementFromPoint({{pos['x']}}, {{pos['y']}}).click();")
                    
                    # 만약 위 코드가 안되면 물리적 클릭 시도
                    # actions.move_by_offset(pos['x'], pos['y']).click().perform()
                    
                    time.sleep(10) 
                    shot_name = f"top_{i+1}.png"
                    driver.save_screenshot(shot_name)
                    send_to_discord(shot_name, f"✅ **{i+1}위: {t_name}** ({theme['rate']})")
                    
                    driver.back()
                    time.sleep(5)
                except Exception as click_err:
                    print(f"⚠️ 클릭 실행 중 오류: {click_err}")
            else:
                print(f"⚠️ {t_name} 위치를 찾을 수 없음")

    except Exception as e:
        print(f"❌ 프로세스 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
