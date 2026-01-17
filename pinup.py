import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

THEME_WEBHOOK = "https://discord.com/api/webhooks/1461690207291310185/TGsuiHItgOU3opyA6Z9NPalUSlSwdZFBWIF2EKPfNNHZbmkmiHywHe4UpXXQGB2b3jEo"

def main():
    print("🚀 [영역 격리] 다른 테마 이름 배제하고 '진짜 종목'만 추출 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=1600,2500')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    final_report = []
    collected_for_start = [] 
    today_date = time.strftime("%m월 %d일")

    try:
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(12)
        
        # 1. TOP 5 테마 이름 먼저 저장 (나중에 종목이랑 헷갈리지 않게 함)
        page_text = driver.find_element(By.TAG_NAME, "body").text
        raw_items = re.findall(r'([가-힣A-Za-z/ ]{2,})\n?([+-]?\d+\.\d+%)', page_text)
        top5 = []
        theme_names_to_exclude = []
        seen = set()
        for name, rate in raw_items:
            clean_name = name.strip()
            if clean_name not in seen and not clean_name.isdigit():
                val = float(rate.replace('%', ''))
                top5.append({'name': clean_name, 'rate': rate, 'val': val})
                theme_names_to_exclude.append(clean_name)
                seen.add(clean_name)
        top5 = sorted(top5, key=lambda x: x['val'], reverse=True)[:5]

        # 2. 테마별 종목 추출
        for i, theme in enumerate(top5):
            t_name = theme['name']
            driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
            time.sleep(8)

            # 테마 클릭
            pos_script = f"var target='{t_name}'; var els=document.querySelectorAll('tspan,text,div'); for(var el of els){{if(el.textContent.trim()===target){{var r=el.getBoundingClientRect(); return {{x:r.left+r.width/2, y:r.top+r.height/2}};}}}} return null;"
            pos = driver.execute_script(pos_script)
            
            stocks_info = []
            if pos:
                driver.execute_script(f"document.elementFromPoint({pos['x']},{pos['y']}).dispatchEvent(new MouseEvent('click',{{bubbles:true}}));")
                time.sleep(8)
                
                # [핵심 변경] 상세 팝업 영역 안의 텍스트만 추출 (바깥쪽 테마 이름 차단)
                extract_script = """
                var btn = Array.from(document.querySelectorAll('*')).find(el => el.textContent.trim() === '테마 상세 >');
                if(btn) {
                    // 버튼의 부모 컨테이너를 찾아서 그 안의 텍스트만 반환
                    var container = btn.closest('div').parentElement;
                    return container.innerText;
                }
                return "";
                """
                detail_area_text = driver.execute_script(extract_script)
                
                # 만약 영역 추출 실패 시 대안 (화면 하단 리스트 영역 타겟팅)
                if not detail_area_text:
                    detail_area_text = driver.execute_script("return document.querySelector('.theme_detail_list') ? document.querySelector('.theme_detail_list').innerText : '';")

                # 종목명(한글/영문/숫자) + 등락률 매칭
                matches = re.findall(r'([가-힣A-Za-z0-9&.]{2,15})\s*([+-]?\d+\.\d+%)', detail_area_text)
                
                s_seen = set()
                for s_name, s_rate in matches:
                    clean_s_name = re.sub(r'^\d{1,2}', '', s_name.strip()) # 순위 숫자 제거
                    
                    # 테마 리스트에 있는 이름이 아니고(중요!), 중복이 아닐 때만
                    if clean_s_name and clean_s_name not in theme_names_to_exclude and clean_s_name not in s_seen:
                        if clean_s_name.isdigit() and len(clean_s_name) <= 3: continue
                            
                        stocks_info.append(f"{clean_s_name} {s_rate}")
                        collected_for_start.append(clean_s_name)
                        s_seen.add(clean_s_name)
                    
                    if len(stocks_info) >= 5: break

            final_report.append({
                "rank": f"{i+1}위", "sector": f"{t_name} ({theme['rate']})",
                "stocks": "<br>".join(stocks_info) if stocks_info else "종목 데이터 추출 실패"
            })

        # 3. 리포트 전송
        summary_msg = f"## 📅 {today_date} 테마 TOP 5 리포트\n| 순위 | 섹터 | 주요 종목 |\n| :--- | :--- | :--- |\n"
        for item in final_report:
            summary_msg += f"| {item['rank']} | **{item['sector']}** | {item['stocks']} |\n"
        
        requests.post(THEME_WEBHOOK, json={'content': summary_msg})
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(list(set(collected_for_start))))
        print("✅ 영역 격리 추출 완료!")

    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
