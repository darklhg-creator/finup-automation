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
    payload = {'content': content}
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                requests.post(DISCORD_WEBHOOK_URL, data=payload, files={'file': f})
        else:
            requests.post(DISCORD_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"디스코드 전송 실패: {e}")

def main():
    print("🚀 핀업 종목 정밀 파싱 시스템 가동...")
    
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
        # 1. 메인 접속 및 TOP 5 리스트 확보
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        raw_items = re.findall(r'([가-힣A-Za-z/ ]{2,})\n?([+-]?\d+\.\d+%)', page_text)
        
        top5 = []
        theme_names = [] # 필터링용
        seen = set()
        for name, rate in raw_items:
            clean_name = name.strip()
            if clean_name not in seen and not clean_name.isdigit():
                val = float(rate.replace('%', ''))
                top5.append({'name': clean_name, 'rate': rate, 'val': val})
                theme_names.append(clean_name)
                seen.add(clean_name)
        
        top5 = sorted(top5, key=lambda x: x['val'], reverse=True)[:5]

        # 2. 각 테마 상세 페이지 진입 및 종목 추출
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"🔍 {i+1}위 분석: {t_name}")
            
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(12)

            # 좌표 추출 로직
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
                time.sleep(10)
                
                # 캡처 전송 (일주일간 확인용)
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(f"📸 **{i+1}위 {t_name}** 상세 캡처", shot_name)
                
                # [핵심] 상세 페이지 내 종목 리스트 영역만 특정하여 추출
                # 핀업 상세 페이지의 종목 리스트는 보통 특정 table이나 list 구조를 가짐
                try:
                    # 종목명이 들어있는 특정 class나 tag를 타겟팅 (범용 정규식 병행)
                    detail_body = driver.find_element(By.TAG_NAME, "body").text
                    
                    # '테마명'들을 제외한 새로운 종목+등락률 패턴 찾기
                    # 보통 종목명 옆에 등락률이 붙어있는 패턴을 추출
                    matches = re.findall(r'([가-힣A-Za-z0-9&]{2,10})\s+([+-]?\d+\.\d+%)', detail_body)
                    
                    for s_name, s_rate in matches:
                        s_name = s_name.strip()
                        # 추출된 이름이 테마 리스트에 있는 이름이 아닐 경우에만 종목으로 인정
                        if s_name not in theme_names and len(stocks_info) < 5:
                            stocks_info.append(f"{s_name} {s_rate}")
                except:
                    pass

            final_report.append({
                "rank": f"{i+1}위",
                "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "종목 데이터 없음"
            })

        # 3. 최종 요약 리포트 전송 (사용자 요청 양식)
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 요약 리포트\n"
        summary_msg += "| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        send_to_discord(summary_msg)
        print("✅ 리포트 생성 완료!")

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
