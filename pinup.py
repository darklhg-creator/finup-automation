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
    print("🚀 [최종 정밀 추출] 종목명에서 숫자 제거 및 이미지+데이터 전송 시작...")
    
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
        # 1. 메인 페이지 접속 및 TOP 5 테마 추출
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15)
        
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
        print(f"🎯 분석 타겟: {[t['name'] for t in top5]}")

        # 2. 테마별 상세 페이지 순회 및 종목 추출
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"🔎 {i+1}위 {t_name} 분석 중...")
            
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(10)

            # 테마 클릭 (좌표 기반)
            pos_script = f"var target='{t_name}'; var els=document.querySelectorAll('tspan,text,div'); for(var el of els){{if(el.textContent.trim()===target){{var r=el.getBoundingClientRect(); return {{x:r.left+r.width/2, y:r.top+r.height/2}};}}}} return null;"
            pos = driver.execute_script(pos_script)
            
            stocks_info = []
            if pos:
                driver.execute_script(f"document.elementFromPoint({pos['x']},{pos['y']}).dispatchEvent(new MouseEvent('click',{{bubbles:true}}));")
                time.sleep(10) # 상세 리스트 로딩 대기
                
                # [캡처본 전송]
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(THEME_WEBHOOK, f"📸 **{i+1}위 {t_name} 상세 리스트**", shot_name)

                # [종목명 정밀 추출] 빨간 박스 영역만 타겟팅
                extract_script = """
                var btn = Array.from(document.querySelectorAll('*')).find(el => el.textContent.trim() === '테마 상세 >');
                if(btn) {
                    return btn.closest('div').parentElement.innerText;
                }
                return document.body.innerText;
                """
                detail_text = driver.execute_script(extract_script)
                
                # 정규식: 한글/영문 포함된 단어(2~12자) + 숫자뭉치(있을수도없을수도) + 등락률
                # ([가-힣A-Za-z]{2,12}) -> 종목명은 반드시 글자로 시작하게 강제
                matches = re.findall(r'([가-힣A-Za-z][가-힣A-Za-z0-9&]{1,12})\s*[0-9]*\s*([+-]?\d+\.\d+%)', detail_text)
                
                s_seen = set()
                for s_name, s_rate in matches:
                    # 앞뒤로 남아있을지 모르는 숫자 노이즈 제거
                    clean_s_name = re.sub(r'^[0-9]+|[0-9]+$', '', s_name.strip()).strip()
                    
                    if clean_s_name and clean_s_name not in theme_names and clean_s_name not in s_seen:
                        stocks_info.append(f"{clean_s_name} {s_rate}")
                        collected_for_start.append(clean_s_name)
                        s_seen.add(clean_s_name)
                    if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위",
                "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "종목 추출 실패"
            })

        # 3. 최종 요약 리포트 전송
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 리포트\n"
        summary_msg += "| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        send_to_discord(THEME_WEBHOOK, summary_msg)
        
        # start.py 연동용 파일 저장
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(list(set(collected_for_start))))
            
        print("✅ 모든 작업 완료! 리포트와 이미지를 확인하세요.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
