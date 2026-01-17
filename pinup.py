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
    print("🚀 [최종 보정] 테마 상세 버튼 기준 종목 추출 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=1600,2000')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    final_report = []
    today_date = time.strftime("%m월 %d일")
    collected_for_start = [] # start.py 전달용

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(12)
        
        # 1. 메인 맵에서 TOP 5 테마 추출 (생략 - 기존 로직 동일)
        # ... (top5 리스트 확보 과정) ...

        for i, theme in enumerate(top5):
            t_name = theme['name']
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(8)

            # [클릭 로직] 테마명 찾아서 클릭
            pos = driver.execute_script(f"var target='{t_name}'; var els=document.querySelectorAll('tspan, text'); for(var el of els){{if(el.textContent.trim()===target){{var r=el.getBoundingClientRect(); return {{x:r.left+r.width/2, y:r.top+r.height/2}};}}}} return null;")
            
            stocks_info = []
            if pos:
                driver.execute_script(f"document.elementFromPoint({pos['x']},{pos['y']}).dispatchEvent(new MouseEvent('click',{{bubbles:true}}));")
                time.sleep(8)
                
                # [이미지 캡처] 먼저 수행
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(THEME_WEBHOOK, f"📸 **{i+1}위 {t_name} 상세**", shot_name)

                # [종목 추출 핵심] '테마 상세 >' 버튼 근처의 표 데이터를 긁어옴
                print(f"🔎 {t_name} 종목 리스트 수집 중...")
                
                # '테마 상세' 버튼 주변의 모든 텍스트를 가져와서 종목명과 등락률 필터링
                extract_script = """
                var result = [];
                // '테마 상세' 글자가 포함된 버튼을 찾음
                var btn = Array.from(document.querySelectorAll('button, a, span')).find(el => el.textContent.includes('테마 상세'));
                if(btn) {
                    // 버튼이 속한 부모 컨테이너(종목 리스트 영역) 전체 텍스트 확보
                    var container = btn.closest('div').parentElement;
                    result.push(container.innerText);
                }
                return result;
                """
                detail_raw = driver.execute_script(extract_script)
                
                if detail_raw:
                    # 정규식으로 종목명(한글/숫자) + 등락률(+0.00%) 추출
                    matches = re.findall(r'([가-힣A-Za-z0-9]{2,10})\s+([+-]?\d+\.\d+%)', str(detail_raw))
                    s_seen = set()
                    for s_name, s_rate in matches:
                        if s_name != t_name and s_name not in s_seen:
                            stocks_info.append(f"{s_name} {s_rate}")
                            collected_for_start.append(f"{s_name}") # start.py용
                            s_seen.add(s_name)
                        if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위", "sector": f"{t_name} ({theme['rate']})", 
                "stocks": "<br>".join(stocks_info) if stocks_info else "종목 데이터 추출 실패"
            })

        # 2. 리포트 전송 및 start.py 연동 파일 저장
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 리포트\n| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        send_to_discord(THEME_WEBHOOK, summary_msg)
        
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(list(set(collected_for_start))))

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
