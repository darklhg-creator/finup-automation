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

def send_to_discord(content, file_path=None):
    """디스코드 웹훅 전송 (텍스트 및 이미지 파일 대응)"""
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                # 파일 전송 시에는 payload를 'content' 키에 담아 전송
                response = requests.post(DISCORD_WEBHOOK_URL, data={'content': content}, files={'file': f})
        else:
            response = requests.post(DISCORD_WEBHOOK_URL, json={'content': content})
        return response.status_code
    except Exception as e:
        print(f"❌ 전송 오류: {e}")
        return None

def main():
    print("🚀 핀업 이미지+데이터 통합 시스템 가동...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,2000') 
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    final_report = []
    today_date = time.strftime("%m월 %d일")

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15)
        
        # 1. TOP 5 리스트 확보
        page_text = driver.find_element(By.TAG_NAME, "body").text
        raw_items = re.findall(r'([가-힣A-Za-z/ ]{2,})\n?([+-]?\d+\.\d+%)', page_text)
        
        top5 = []
        theme_names = []
        seen = set()
        for name, rate in raw_items:
            clean_name = name.strip()
            if clean_name not in seen and not clean_name.isdigit():
                val = float(rate.replace('%', ''))
                top5.append({'name': clean_name, 'rate': rate, 'val': val})
                theme_names.append(clean_name)
                seen.add(clean_name)
        top5 = sorted(top5, key=lambda x: x['val'], reverse=True)[:5]
        print(f"🎯 타겟 확정: {[t['name'] for t in top5]}")

        # 2. 각 테마 정밀 추적 및 분석
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"📡 {i+1}위 추적: {t_name}")
            
            # 매 사이클마다 메인 페이지에서 시작 (안정성 확보)
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(12)

            get_real_pos_script = f"""
            var target = "{t_name}";
            var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            var node;
            while(node = walker.nextNode()) {{
                if (node.textContent.trim() === target) {{
                    var range = document.createRange();
                    range.selectNodeContents(node);
                    var rect = range.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {{
                        return {{x: rect.left + rect.width/2, y: rect.top + rect.height/2}};
                    }}
                }}
            }}
            return null;
            """
            pos = driver.execute_script(get_real_pos_script)
            
            stocks_info = []
            if pos:
                print(f"🎯 {t_name} 클릭 지점: ({pos['x']}, {pos['y']})")
                
                # 정밀 클릭 발사
                click_script = f"""
                var x = {pos['x']}; var y = {pos['y']};
                var el = document.elementFromPoint(x, y);
                if (el) {{
                    ['mousedown', 'click', 'mouseup'].forEach(evt => {{
                        el.dispatchEvent(new MouseEvent(evt, {{bubbles: true, clientX: x, clientY: y}}));
                    }});
                }}
                """
                driver.execute_script(click_script)
                time.sleep(10) # 상세 페이지 로딩 대기

                # [이미지 저장 및 전송]
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(f"📸 **{i+1}위 {t_name} 상세 화면**", shot_name)
                
                # [데이터 추출]
                detail_text = driver.find_element(By.TAG_NAME, "body").text
                # 종목명(한글/숫자/영문) + 등락률 패턴
                stock_matches = re.findall(r'([가-힣A-Za-z0-9&]{2,12})\s+([+-]?\d+\.\d+%)', detail_text)
                
                s_seen = set()
                for s_name, s_rate in stock_matches:
                    s_name = s_name.strip()
                    # 테마명 제외 및 중복 방지
                    if s_name not in theme_names and s_name not in s_seen:
                        stocks_info.append(f"{s_name} {s_rate}")
                        s_seen.add(s_name)
                    if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위",
                "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "종목 데이터 추출 실패"
            })

        # 3. 최종 요약 표 리포트 생성 및 전송
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 요약 리포트\n"
        summary_msg += "| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        send_to_discord(summary_msg)
        print("✅ 모든 리포트 및 이미지 전송 완료!")

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
