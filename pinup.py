import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 1. 전달해주신 웹훅 주소 설정
THEME_WEBHOOK = "https://discord.com/api/webhooks/1461690207291310185/TGsuiHItgOU3opyA6Z9NPalUSlSwdZFBWIF2EKPfNNHZbmkmiHywHe4UpXXQGB2b3jEo"
IGYEOK_WEBHOOK = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def send_to_discord(webhook_url, content, file_path=None):
    """지정된 채널 웹훅으로 텍스트 또는 파일을 전송"""
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                requests.post(webhook_url, data={'content': content}, files={'file': f})
        else:
            requests.post(webhook_url, json={'content': content})
    except Exception as e:
        print(f"❌ 전송 오류: {e}")

def main():
    print("🚀 테마록(핀업) 채널 전송 시스템 가동...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,2500') # 충분한 높이 확보
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    final_report = []
    today_date = time.strftime("%m월 %d일")

    try:
        # 메인 페이지 접속
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15)
        
        # 1. 전체 테마명 리스트 확보 (필터링용)
        page_text = driver.find_element(By.TAG_NAME, "body").text
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

        # 2. 각 테마 상세 분석 (테마록 채널로 전송)
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"📡 {i+1}위 추적: {t_name}")
            
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(12)

            # 정밀 좌표 찾기
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
                # 관통 클릭 및 로딩 대기
                driver.execute_script(f"document.elementFromPoint({pos['x']}, {pos['y']}).dispatchEvent(new MouseEvent('click', {{bubbles:true}}));")
                time.sleep(10)
                
                # 하단 종목 리스트 로딩을 위한 스크롤
                driver.execute_script("window.scrollTo(0, 1000);")
                time.sleep(5)
                
                # [이미지 전송] 테마록 채널로!
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(THEME_WEBHOOK, f"📸 **{i+1}위 {t_name} 상세**", shot_name)
                
                # [종목 데이터 파싱 보강]
                detail_body = driver.find_element(By.TAG_NAME, "body").text
                # 종목명과 등락률 패턴 매칭 (이름 2~12자 + 공백 + 퍼센트)
                matches = re.findall(r'([가-힣A-Za-z0-9&]{2,12})\s+([+-]?\d+\.\d+%)', detail_body)
                
                s_seen = set()
                for s_name, s_rate in matches:
                    s_name = s_name.strip()
                    # 테마 리스트에 있는 이름이 아니고, 중복이 아닐 때만 종목으로 인정
                    if s_name not in all_theme_names and s_name not in s_seen:
                        stocks_info.append(f"{s_name} {s_rate}")
                        s_seen.add(s_name)
                    if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위",
                "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "종목 로딩 지연"
            })

        # 3. 최종 요약 리포트 전송 (테마록 채널로!)
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 리포트\n"
        summary_msg += "| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        send_to_discord(THEME_WEBHOOK, summary_msg)
        print("✅ 테마록 채널로 모든 전송 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
