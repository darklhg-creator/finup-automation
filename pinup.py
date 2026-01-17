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

def send_to_discord_image(file_path, title):
    """이미지를 먼저 개별적으로 전송"""
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            requests.post(DISCORD_WEBHOOK_URL, data={'content': title}, files={'file': f})

def send_to_discord_text(content):
    """최종 리포트 전송"""
    requests.post(DISCORD_WEBHOOK_URL, json={'content': content})

def main():
    print("🚀 핀업 이미지 우선 전송 및 데이터 추출 시스템 가동...")
    
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

        # 2. 상세 분석 및 이미지 선전송
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"🔍 {i+1}위 작업: {t_name}")
            
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(12)

            find_pos_script = f"""
            var target = "{t_name}";
            var els = document.querySelectorAll('tspan, text');
            for (var el of els) {{
                if (el.textContent.trim() === target) {{
                    var r = el.getBoundingClientRect();
                    return {{x: r.left + r.width/2, y: r.top + r.height/2}};
                }}
            }}
            return null;
            """
            pos = driver.execute_script(find_pos_script)
            
            stocks_info = []
            if pos:
                # 관통 클릭
                driver.execute_script(f"document.elementFromPoint({pos['x']}, {pos['y']}).dispatchEvent(new MouseEvent('click', {{bubbles:true}}));")
                time.sleep(8)
                
                # 상세 페이지 스크롤 (데이터 로딩 유도)
                driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(5)
                
                # [즉시 전송] 캡처 이미지를 먼저 디코로 보냄
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord_image(shot_name, f"📸 **{i+1}위 {t_name}** 상세 화면")
                
                # 데이터 추출
                detail_body = driver.find_element(By.TAG_NAME, "body").text
                # 종목명(한글/숫자/영문) + 등락률 패턴 (더 느슨하게)
                matches = re.findall(r'([가-힣A-Za-z0-9&]{2,12})\s+([+-]?\d+\.\d+%)', detail_body)
                
                s_seen = set()
                for s_name, s_rate in matches:
                    s_name = s_name.strip()
                    # 테마명이 아니고 중복이 아닌 것만 수집
                    if s_name not in theme_names and s_name not in s_seen:
                        stocks_info.append(f"{s_name} {s_rate}")
                        s_seen.add(s_name)
                    if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위",
                "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "종목 데이터 없음"
            })

        # 3. 최종 요약 리포트 전송
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 요약 리포트\n"
        summary_msg += "| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        send_to_discord_text(summary_msg)
        print("✅ 모든 전송 완료!")

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
