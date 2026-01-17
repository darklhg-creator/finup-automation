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
    print("⚡ 핀업 개별 테마 '정밀 픽셀 좌표' 추출 시스템 가동...")
    
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
        
        # 1. TOP 5 리스트 확보
        page_text = driver.find_element(By.TAG_NAME, "body").text
        raw_items = re.findall(r'([가-힣A-Za-z/ ]{2,})\n?([+-]?\d+\.\d+%)', page_text)
        
        top5 = []
        seen = set()
        for name, rate in raw_items:
            clean_name = name.strip()
            if clean_name not in seen and not clean_name.isdigit():
                val = float(rate.replace('%', ''))
                top5.append({'name': clean_name, 'rate': rate, 'val': val})
                seen.add(clean_name)
        
        top5 = sorted(top5, key=lambda x: x['val'], reverse=True)[:5]
        print(f"🎯 타겟 확정: {[t['name'] for t in top5]}")

        # 2. 개별 테마의 '진짜 좌표'를 찾아서 클릭
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"📡 {i+1}위 정밀 추적 중: {t_name}")
            
            # [획기적 스크립트] 텍스트가 포함된 모든 노드를 뒤져서 '실제 위치'를 반환
            get_real_pos_script = f"""
            var target = "{t_name}";
            // 1. 모든 텍스트 노드를 전수조사
            var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            var node;
            while(node = walker.nextNode()) {{
                if (node.textContent.includes(target)) {{
                    var range = document.createRange();
                    range.selectNodeContents(node);
                    var rect = range.getBoundingClientRect();
                    // 0,0이 아니고 크기가 있는 진짜 글자 위치라면 반환
                    if (rect.width > 0 && rect.height > 0) {{
                        return {{x: rect.left + rect.width/2, y: rect.top + rect.height/2}};
                    }}
                }}
            }}
            // 2. 만약 실패하면 SVG 텍스트 태그 재조사
            var svgTexts = document.querySelectorAll('tspan, text');
            for (var st of svgTexts) {{
                if (st.textContent.includes(target)) {{
                    var r = st.getBoundingClientRect();
                    return {{x: r.left + r.width/2, y: r.top + r.height/2}};
                }}
            }}
            return null;
            """
            
            pos = driver.execute_script(get_real_pos_script)
            
            if pos:
                print(f"🎯 {t_name} 진짜 좌표 발견: ({pos['x']}, {pos['y']})")
                
                # 강제 관통 클릭 발사
                click_script = f"""
                var x = {pos['x']};
                var y = {pos['y']};
                var el = document.elementFromPoint(x, y);
                if (el) {{
                    ['mousedown', 'click', 'mouseup'].forEach(evt => {{
                        var e = new MouseEvent(evt, {{bubbles: true, clientX: x, clientY: y}});
                        el.dispatchEvent(e);
                    }});
                }}
                """
                driver.execute_script(click_script)
                
                time.sleep(10) # 상세 로딩 대기
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(shot_name, f"✅ **{i+1}위: {t_name}** ({theme['rate']})")
                
                # 다시 메인으로 복구
                driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
                time.sleep(10)
            else:
                print(f"⚠️ {t_name}의 진짜 좌표를 찾지 못했습니다.")

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
