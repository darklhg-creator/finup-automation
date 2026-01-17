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
    print("🚀 [최종 보정] 영문/한글 혼합 종목명 정밀 추출 시작...")
    
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
        # 1. 메인 페이지 접속 및 테마 TOP 5 추출
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        # 테마명과 등락률 패턴 추출
        raw_items = re.findall(r'([가-힣A-Za-z/ ]{2,})\n?([+-]?\d+\.\d+%)', page_text)
        
        top5 = []
        all_theme_names = []
        seen = set()
        for name, rate in raw_items:
            clean_name = name.strip()
            if clean_name not in seen and not clean_name.isdigit():
                val = float(rate.replace('%', ''))
                top5.append({'name': clean_name, 'rate': rate, 'val': val})
                all_theme_names.append(clean_name)
                seen.add(clean_name)
        
        top5 = sorted(top5, key=lambda x: x['val'], reverse=True)[:5]
        print(f"🎯 테마 타겟 확정: {[t['name'] for t in top5]}")

        # 2. 각 테마 상세 분석
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"📡 {i+1}위 추적 중: {t_name}")
            
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(12)

            # 테마 클릭을 위한 좌표 찾기
            pos_script = f"""
            var target = "{t_name}";
            var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            var node;
            while(node = walker.nextNode()) {{
                if (node.textContent.trim() === target) {{
                    var range = document.createRange();
                    range.selectNodeContents(node);
                    var rect = range.getBoundingClientRect();
                    if (rect.width > 0) return {{x: rect.left + rect.width/2, y: rect.top + rect.height/2}};
                }}
            }}
            return null;
            """
            pos = driver.execute_script(pos_script)
            
            stocks_info = []
            if pos:
                driver.execute_script(f"document.elementFromPoint({pos['x']}, {pos['y']}).dispatchEvent(new MouseEvent('click', {{bubbles:true}}));")
                time.sleep(10)
                
                # 이미지 캡처 및 전송
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(THEME_WEBHOOK, f"📸 **{i+1}위 {t_name} 상세**", shot_name)
                
                # [핵심] 종목 추출 로직: % 기호 앞의 텍스트를 가져와서 앞쪽 순위 숫자만 제거
                detail_text = driver.execute_script("return document.body.innerText;")
                
                # 패턴: (한글/영문/숫자 혼합 2~15자) + (공백) + (등락률%)
                matches = re.findall(r'([가-힣A-Za-z0-9&.]{2,15})\s*([+-]?\d+\.\d+%)', detail_text)
                
                s_seen = set()
                for s_name, s_rate in matches:
                    raw_s_name = s_name.strip()
                    
                    # 1. 종목명 앞에 붙은 순위 숫자(1, 2, 3...)만 제거
                    clean_s_name = re.sub(r'^\d{1,2}', '', raw_s_name)
                    
                    # 2. 유효성 검사: 테마명이 아니고, 중복이 아니며, 순수 숫자로만 된 단축코드 제외
                    if clean_s_name and clean_s_name != t_name and clean_s_name not in s_seen:
                        if clean_s_name.isdigit() and len(clean_s_name) <= 3:
                            continue # '680' 같은 찌꺼기 방지
                            
                        stocks_info.append(f"{clean_s_name} {s_rate}")
                        collected_for_start.append(clean_s_name)
                        s_seen.add(clean_s_name)
                        
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
        
        # start.py와 공유할 파일 저장
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(list(set(collected_for_start))))
            
        print("✅ 모든 작업이 완료되었습니다!")

    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
