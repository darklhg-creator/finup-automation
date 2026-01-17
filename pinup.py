import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 채널별 웹훅 주소
THEME_WEBHOOK = "https://discord.com/api/webhooks/1461690207291310185/TGsuiHItgOU3opyA6Z9NPalUSlSwdZFBWIF2EKPfNNHZbmkmiHywHe4UpXXQGB2b3jEo"

def send_to_discord(webhook_url, content, file_path=None):
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                requests.post(webhook_url, data={'content': content}, files={'file': f})
        else:
            requests.post(webhook_url, json={'content': content})
    except Exception as e:
        print(f"❌ 전송 오류: {e}")

def main():
    print("🚀 [위치 고정 방식] 테마 상세 버튼 하단 5종목 정밀 추출 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,2500')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    final_report = []
    collected_for_start = [] 
    today_date = time.strftime("%m월 %d일")

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15)
        
        # 1. 메인 맵에서 TOP 5 추출 (이 부분은 정상 작동 확인됨)
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
        print(f"🎯 분석 타겟: {[t['name'] for t in top5]}")

        # 2. 테마별 상세 페이지 순회
        for i, theme in enumerate(top5):
            t_name = theme['name']
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(10)

            # 테마 클릭 (좌표 기반)
            pos_script = f"""
            var target = "{t_name}";
            var els = document.querySelectorAll('tspan, text, div');
            for(var el of els) {{
                if(el.textContent.trim() === target) {{
                    var r = el.getBoundingClientRect();
                    return {{x: r.left + r.width/2, y: r.top + r.height/2}};
                }}
            }}
            return null;
            """
            pos = driver.execute_script(pos_script)
            
            stocks_info = []
            if pos:
                driver.execute_script(f"document.elementFromPoint({pos['x']}, {pos['y']}).dispatchEvent(new MouseEvent('click', {{bubbles:true}}));")
                time.sleep(10)
                
                # [캡처본 전송]
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(THEME_WEBHOOK, f"📸 **{i+1}위 {t_name} 상세**", shot_name)

                # [종목 정밀 추출] 파란색 영역(테마 상세 하단)을 직접 타겟팅
                print(f"🔎 {t_name} 종목 데이터 수집 중...")
                extract_script = """
                var result = [];
                // '테마 상세' 텍스트를 가진 요소를 찾음
                var btn = Array.from(document.querySelectorAll('*')).find(el => el.textContent.trim() === '테마 상세 >');
                if(btn) {
                    // 버튼의 조상 중 종목 리스트를 감싸는 가장 가까운 컨테이너를 찾음
                    var container = btn.closest('div').parentElement.parentElement;
                    // 컨테이너 내부의 모든 텍스트 행을 긁어옴
                    return container.innerText;
                }
                return "";
                """
                raw_data = driver.execute_script(extract_script)
                
                if raw_data:
                    # 종목명(한글/영문) + 등락률 패턴만 정밀 필터링
                    # 한글/영문 2자 이상 + 공백 + +XX.XX%
                    matches = re.findall(r'([가-힣A-Za-z]{2,10})\s+([+-]?\d+\.\d+%)', raw_data)
                    
                    s_seen = set()
                    for s_name, s_rate in matches:
                        if s_name != t_name and s_name not in s_seen:
                            stocks_info.append(f"{s_name} {s_rate}")
                            collected_for_start.append(f"{s_name}")
                            s_seen.add(s_name)
                        if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위",
                "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "종목 추출 실패"
            })

        # 3. 요약 리포트 전송
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 리포트\n"
        summary_msg += "| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        send_to_discord(THEME_WEBHOOK, summary_msg)
        
        # start.py 연동용 파일 저장
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(list(set(collected_for_start))))
            
        print("✅ 테마록 채널
