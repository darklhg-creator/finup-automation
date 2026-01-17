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
    """텍스트와 이미지를 디스코드로 전송"""
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
    print("🚀 핀업 이미지+데이터 통합 추출 시스템 가동 (문법 수정판)...")
    
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
        seen = set()
        for name, rate in raw_items:
            clean_name = name.strip()
            if clean_name not in seen and not clean_name.isdigit():
                val = float(rate.replace('%', ''))
                top5.append({'name': clean_name, 'rate': rate, 'val': val})
                seen.add(clean_name)
        
        top5 = sorted(top5, key=lambda x: x['val'], reverse=True)[:5]
        print(f"🎯 타겟 확정: {[t['name'] for t in top5]}")

        # 2. 개별 테마 상세 분석
        for i, theme in enumerate(top5):
            t_name = theme['name']
            print(f"🔍 {i+1}위 작업 중: {t_name}")
            
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(12)

            find_pos_script = f"""
            var target = "{t_name}";
            var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
            var node;
            while(node = walker.nextNode()) {{
                if (node.textContent.includes(target)) {{
                    var range = document.createRange();
                    range.selectNodeContents(node);
                    var rect = range.getBoundingClientRect();
                    if (rect.width > 0) return {{x: rect.left + rect.width/2, y: rect.top + rect.height/2}};
                }}
            }}
            return null;
            """
            pos = driver.execute_script(find_pos_script)
            
            stocks_info = []
            if pos:
                # 관통 클릭
                driver.execute_script(f"var el = document.elementFromPoint({pos['x']}, {pos['y']}); if(el) el.click();")
                time.sleep(10)
                
                # A. 이미지 캡처 및 전송
                shot_name = f"top_{i+1}.png"
                driver.save_screenshot(shot_name)
                send_to_discord(f"📸 **{i+1}위 {t_name} 상세 화면**", shot_name)
                
                # B. 데이터 추출 (상세 페이지 텍스트 분석)
                detail_text = driver.find_element(By.TAG_NAME, "body").text
                stock_matches = re.findall(r'([가-힣A-Za-z0-9]+)\s+([+-]?\d+\.\d+%)', detail_text)
                
                # 중복 제거 및 상위 5개
                s_seen = set()
                for s_name, s_rate in stock_matches:
                    if s_name not in s_seen and s_name != t_name:
                        stocks_info.append(f"{s_name} {s_rate}")
                        s_seen.add(s_name)
                    if len(stocks_info) >= 5: break

            # 리포트용 데이터 저장
            final_report.append({
                "rank": f"{i+1}위",
                "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "추출 실패"
            })

        # 3. 최종 요약 리포트 전송
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 요약 리포트\n"
        summary_msg += "| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            # f-string 내부가 아닌 외부에서 미리 처리
            r = item['rank']
            s = item['sector']
            st = item['stocks']
            summary_msg += f"| {r} | **{s}** | {st} |\n"
        
        send_to_discord(summary_msg)
        print("✅ 모든 작업 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()
