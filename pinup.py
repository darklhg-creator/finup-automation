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
    print("🚀 핀업 최종 좌표 타격 및 5단계 캡처 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # 모든 요소가 보일 수 있게 창 크기를 충분히 크게 설정
    chrome_options.add_argument('--window-size=1600,3000')
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

        print(f"✅ 타겟 확정: {[t['name'] for t in top5]}")

        # 2. 물리적 좌표 클릭 시퀀스
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"🔍 {i+1}위 추적 및 클릭: {t_name}")
            
            # 자바스크립트로 좌표만 가져오기 (스크롤 포함)
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
            time.sleep(3) # 화면 안정화

            if pos:
                print(f"🎯 좌표 타격 지점: ({pos['x']}, {pos['y']})")
                try:
                    # ActionChains를 사용한 정밀 물리 클릭
                    # 0,0(좌상단) 기준으로 마우스를 이동시켜 클릭합니다.
                    actions = ActionChains(driver)
                    actions.move_by_offset(pos['x'], pos['y']).click().perform()
                    # 다음 클릭을 위해 마우스 위치 초기화
                    actions.move_by_offset(-pos['x'], -pos['y']).perform()
                    
                    time.sleep(10) # 상세 페이지 로딩 대기
                    
                    shot_name = f"top_{i+1}.png"
                    driver.save_screenshot(shot_name)
                    send_to_discord(shot_name, f"✅ **{i+1}위 상세: {t_name}** ({theme['rate']})")
                    
                    driver.back() # 다시 메인으로
                    time.sleep(5)
                except Exception as click_err:
                    print(f"⚠️ 클릭 실패: {click_err}")
                    # 클릭 실패시 강제 URL 이동 등의 플랜B를 쓸 수 있지만 일단 물리 클릭에 집중
            else:
                print(f"⚠️ {t_name} 위치를 찾을 수 없습니다.")

    except Exception as e:
        print(f"❌ 프로세스 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
