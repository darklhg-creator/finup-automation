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
    print("🚀 [재시작] 슬래시(/) 구분자 버전 리포트 생성 시작...")
    
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
        time.sleep(30)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        raw_items = re.findall(r'([가-힣A-Za-z/ ]{2,})\n?([+-]?\d+\.\d+%)', page_text)
        
        top5 = []
        theme_names = []
        seen = set()
        for name, rate in raw_items:
            c_name = name.strip()
            if c_name not in seen and not c_name.isdigit():
                top5.append({'name': c_name, 'rate': rate, 'val': float(rate.replace('%',''))})
                theme_names.append(c_name)
                seen.add(c_name)
        
        top5 = sorted(top5, key=lambda x: x['val'], reverse=True)[:5]
        print(f"🎯 테마 타겟 확정: {[t['name'] for t in top5]}")

        # 2. 테마별 상세 분석
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"📡 {i+1}위 분석 중: {t_name}")
            
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(30)

            # 테마 클릭
            click_js = f"""
            var target = '{t_name}';
            var els = document.querySelectorAll('tspan, text, div');
            for(var el of els) {{
                if(el.textContent.trim() === target) {{
                    el.dispatchEvent(new MouseEvent('click', {{bubbles:true}}));
                    return true;
                }}
            }}
            return false;
            """
            driver.execute_script(click_js)
            time.sleep(30)
            
            # 캡처 전송
            shot_name = f"top_{i+1}.png"
            driver.save_screenshot(shot_name)
            send_to_discord(THEME_WEBHOOK, f"📸 **{i+1}위 {t_name} 상세 화면**", shot_name)

            # 상세 리스트 텍스트 추출
            list_js = """
            var list = document.querySelectorAll('.theme_detail_list li, .detail_list li, tr');
            return Array.from(list).map(el => el.innerText.replace(/\\n/g, ' ').trim());
            """
            raw_lines = driver.execute_script(list_js)
            
            stocks_info = []
            s_seen = set()
            
            for line in raw_lines:
                if '%' in line and not any(tn in line[:10] for tn in theme_names):
                    if len(line) < 5 or line in s_seen: continue
                    
                    stocks_info.append(line)
                    
                    # targets.txt용 종목명만 추출
                    name_match = re.search(r'([가-힣A-Za-z&.]{2,})', line)
                    if name_match:
                        collected_for_start.append(name_match.group(1))
                    
                    s_seen.add(line)
                    if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위",
                "sector": f"{t_name} ({theme['rate']})",
                "stocks": " / ".join(stocks_info) if stocks_info else "데이터 추출 실패"
            })

        # 3. 리포트 전송
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 리포트\n"
        summary_msg += "| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        send_to_discord(THEME_WEBHOOK, summary_msg)
        
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(list(set(collected_for_start))))
            
        print("✅ 모든 작업이 드디어 완료되었습니다!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
