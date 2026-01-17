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

def main():
    print("🚀 [종목명-코드 매칭 보정] 추출 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=1600,2500')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    final_report = []
    collected_for_start = [] 

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15)
        
        # TOP 5 테마 추출 로직 (동일)
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

        for i, theme in enumerate(top5):
            t_name = theme['name']
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(10)

            # 테마 클릭 로직 (좌표 기반)
            pos_script = f"var target='{t_name}'; var els=document.querySelectorAll('tspan,text,div'); for(var el of els){{if(el.textContent.trim()===target){{var r=el.getBoundingClientRect(); return {{x:r.left+r.width/2, y:r.top+r.height/2}};}}}} return null;"
            pos = driver.execute_script(pos_script)
            
            stocks_info = []
            if pos:
                driver.execute_script(f"document.elementFromPoint({pos['x']},{pos['y']}).dispatchEvent(new MouseEvent('click',{{bubbles:true}}));")
                time.sleep(10)
                
                # 상세 데이터 텍스트 긁기
                # 버튼 주변 컨테이너의 innerText를 직접 가져와서 노이즈를 줄임
                extract_script = """
                var btn = Array.from(document.querySelectorAll('*')).find(el => el.textContent.trim() === '테마 상세 >');
                if(btn) {
                    return btn.closest('div').parentElement.innerText;
                }
                return document.body.innerText;
                """
                detail_text = driver.execute_script(extract_script)
                
                # [수정된 정규식] 
                # 숫자가 섞인 단어는 버리고, 순수 한글/영문(2~10자)만 종목으로 인정
                # 등락률(%) 앞의 텍스트를 정밀하게 분리
                matches = re.findall(r'([가-힣]{2,10})\s*[0-9]*\s*([+-]?\d+\.\d+%)', detail_text)
                
                s_seen = set()
                for s_name, s_rate in matches:
                    s_name = s_name.strip()
                    if s_name != t_name and s_name not in s_seen:
                        stocks_info.append(f"{s_name} {s_rate}")
                        collected_for_start.append(f"{s_name}")
                        s_seen.add(s_name)
                    if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위", "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "추출 실패"
            })

        # 리포트 전송 및 파일 저장
        summary_msg = f"## 📅 테마 TOP 5 리포트\n| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        requests.post(THEME_WEBHOOK, json={'content': summary_msg})
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(list(set(collected_for_start))))

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
