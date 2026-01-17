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
    print("🚀 핀업 무적 좌표 타격 시스템 가동 (새로고침 모드)...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,3000')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 1. 먼저 TOP 5 명단부터 확실히 확보
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15)
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
        target_names = [t['name'] for t in top5]
        target_rates = {t['name']: t['rate'] for t in top5}

        print(f"🎯 최종 타겟 확정: {target_names}")

        # 2. 각 타겟별로 독립적인 사이클 진행 (가장 확실한 방법)
        for i, t_name in enumerate(target_names):
            print(f"🔍 {i+1}위 작업 시작: {t_name}")
            
            # 매번 새로 접속해서 깨끗한 화면에서 시작 (에러 방지 핵심)
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(12) 
            
            # 좌표 찾기
            find_script = f"""
            var target = "{t_name}";
            var els = document.querySelectorAll('tspan, text, div, span');
            for (var el of els) {{
                if (el.textContent.includes(target)) {{
                    el.scrollIntoView({{block: "center", inline: "center"}});
                    var r = el.getBoundingClientRect();
                    return {{x: Math.round(r.left + r.width/2), y: Math.round(r.top + r.height/2)}};
                }}
            }}
            return null;
            """
            pos = driver.execute_script(find_script)
            time.sleep(2)

            if pos:
                print(f"🎯 {t_name} 좌표 발견: ({pos['x']}, {pos['y']})")
                try:
                    actions = ActionChains(driver)
                    # body 요소를 기준으로 절대 좌표 클릭 (누적 방지)
                    body = driver.find_element(By.TAG_NAME, "body")
                    actions.move_to_element_with_offset(body, pos['x'], pos['y']).click().perform()
                    
                    time.sleep(10) # 상세 페이지 로딩 대기
                    
                    shot_name = f"top_{i+1}.png"
                    driver.save_screenshot(shot_name)
                    send_to_discord(shot_name, f"✅ **{i+1}위 상세: {t_name}** ({target_rates[t_name]})")
                except Exception as click_err:
                    print(f"⚠️ {t_name} 클릭 중 오류: {click_err}")
            else:
                print(f"⚠️ {t_name} 위치를 찾지 못했습니다. (지도가 덜 그려졌을 수 있음)")

    except Exception as e:
        print(f"❌ 전체 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
