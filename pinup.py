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
    print("🚀 [통합 추출] 상세 리스트의 데이터를 가공 없이 정확하게 추출 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=1600,2500')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    final_report = []
    collected_for_start = [] 
    today_date = time.strftime("%m월 %d일")

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(12)
        
        # 1. TOP 5 테마 이름 수집 (중복 배제용)
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

        # 2. 테마별 상세 분석
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"📡 {i+1}위 추적: {t_name}")
            
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(8)

            # 테마 클릭
            click_js = f"""
            var els = document.querySelectorAll('tspan, text, div');
            for(var el of els) {{
                if(el.textContent.trim() === '{t_name}') {{
                    el.dispatchEvent(new MouseEvent('click', {{bubbles:true}}));
                    return true;
                }}
            }}
            return false;
            """
            driver.execute_script(click_js)
            time.sleep(8)
            
            # 캡처 전송
            shot_name = f"top_{i+1}.png"
            driver.save_screenshot(shot_name)
            send_to_discord(THEME_WEBHOOK, f"📸 **{i+1}위 {t_name} 상세 화면**", shot_name)

            # [핵심] 리스트의 텍스트 한 줄씩 통째로 가져오기
            stocks_js = """
            var list = document.querySelectorAll('.theme_detail_list li, .detail_list li, tr');
            return Array.from(list).map(el => el.innerText.replace(/\\n/g, ' ').trim());
            """
            raw_lines = driver.execute_script(stocks_js)
            
            stocks_info = []
            s_seen = set()
            
            for line in raw_lines:
                # '%'가 포함되어 있고, 테마 이름이 아닌 '진짜 종목 줄'만 필터링
                if '%' in line and not any(tn in line[:10] for tn in theme_names):
                    # 너무 짧거나 의미 없는 데이터 방지
                    if len(line) < 5: continue
                    
                    # 리스트에 추가 (모베이스전자012680 5,400 +29.98% 형태 유지)
                    stocks_info.append(line)
                    
                    # targets.txt용 이름 추출 (숫자 떼기 힘들면 일단 통째로 저장)
                    # 나중에 start.py가 인식하기 좋게 한글/영문 부분만 저장
                    name_match = re.search(r'([가-힣A-Za-z&.]{2,})', line)
                    if name_match:
                        collected_for_start.append(name_match.group(1))
                    
                    s_seen.add(line)
                
                if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위", "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "데이터 로딩 대기 중..."
            })

        # 3. 리포트 전송
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 리포트\n| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        send_to_discord(THEME_WEBHOOK, summary_msg)
        
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(list(set(collected_for_start))))
        print("✅ 리포트 전송 완료!")

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
