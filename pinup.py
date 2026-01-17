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
    print("🚀 핀업 파편화된 텍스트 좌표 정밀 클릭 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,1200')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(20) # 차트가 완전히 렌더링될 때까지 넉넉히 대기

        # 1. TOP 5 리스트 확보 (이미 검증된 로직)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        raw_items = re.findall(r'([가-힣A-Za-z/ ]{2,})\n?([+-]?\d+\.\d+%)', page_text)
        
        extracted = []
        for name, rate in raw_items:
            val = float(rate.replace('%', ''))
            clean_name = name.strip()
            if not clean_name.isdigit():
                extracted.append({'name': clean_name, 'rate': rate, 'val': val})
        
        unique_top = {item['name']: item for item in extracted}.values()
        top5 = sorted(unique_top, key=lambda x: x['val'], reverse=True)[:5]

        print(f"✅ 타겟팅 리스트: {[t['name'] for t in top5]}")

        # 2. 파편화된 텍스트 요소 강제 추적 및 클릭
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"🔍 {i+1}위 추적 중: {t_name}")
            
            # JavaScript로 텍스트 조각 위치 찾기 (정밀 모드)
            find_script = f"""
            var target = "{t_name}";
            var shortTarget = target.substring(0, 2); // '정원오' -> '정원'
            var allElements = document.querySelectorAll('tspan, text, div, span, [class*="point"]');
            
            for (var el of allElements) {{
                var txt = el.textContent.trim();
                // 전체 일치 혹은 부분 일치 확인
                if (txt === target || (txt.length >= 2 && target.includes(txt)) || txt.includes(shortTarget)) {{
                    var rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {{
                        return {{x: rect.left + rect.width/2, y: rect.top + rect.height/2}};
                    }}
                }}
            }}
            return null;
            """
            pos = driver.execute_script(find_script)
            
            if pos:
                print(f"🎯 좌표 발견: ({pos['x']}, {pos['y']}) - 클릭 시도")
                actions = ActionChains(driver)
                # 뷰포트 기준 절대 좌표 클릭
                actions.move_to_element_with_offset(driver.find_element(By.TAG_NAME, "body"), pos['x'], pos['y']).click().perform()
                
                time.sleep(12) # 상세 페이지 로딩 대기
                
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(shot_name, f"✅ **{i+1}위 상세: {t_name}** ({theme['rate']})")
                
                driver.back() # 메인 맵으로 복귀
                time.sleep(5)
            else:
                print(f"⚠️ {t_name} 위치 파악 불가. 무시하고 다음 섹터 진행.")

    except Exception as e:
        print(f"❌ 전체 프로세스 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
