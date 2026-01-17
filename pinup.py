import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 디스코드 웹훅 주소
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def main():
    print("🚀 핀업 테마 분석 시작 (최종 리포트 생성 모드)...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1200,1200')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # 리포트 머리말
    report_msg = "📊 **핀업(Finup) 실시간 테마 TOP 5 리포트**\n"
    report_msg += "==========================================\n\n"

    try:
        url = "https://finup.co.kr/StockTheme/ThemeMain"
        driver.get(url)
        time.sleep(12) # 페이지 전체 로딩 대기

        # 상위 테마 5개 요소 찾기
        items = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")[:5]
        
        if not items:
            print("❌ 데이터를 찾지 못했습니다.")
            return

        for i in range(len(items)):
            try:
                # 루프마다 엘리먼트 갱신 (클릭 후 DOM 변화 방지)
                current_items = driver.find_elements(By.CSS_SELECTOR, ".theme_item_list .item")
                target = current_items[i]
                
                # 테마명과 등락률 추출
                t_name = target.find_element(By.CSS_SELECTOR, ".name").text.strip()
                t_rate = target.find_element(By.CSS_SELECTOR, ".rate").text.strip()
                
                # 해당 테마 클릭 (하단 종목 리스트 갱신)
                driver.execute_script("arguments[0].click();", target)
                time.sleep(3) # 하단 종목 로딩 대기
                
                # 하단 종목 리스트 5개 추출
                stock_elements = driver.find_elements(By.CSS_SELECTOR, ".stock_list_table .stock_name")[:5]
                stocks = [s.text.strip() for s in stock_elements if s.text.strip()]
                
                # 리포트에 추가
                report_msg += f"{i+1}위: 🔥 **{t_name}** ({t_rate})\n"
                report_msg += f"└ 종목: {', '.join(stocks) if stocks else '종목 정보 없음'}\n\n"
                
                print(f"✅ {i+1}위 {t_name} 데이터 정리 완료")

            except Exception as e:
                print(f"⚠️ {i+1}위 추출 중 오류 발생: {e}")

        # 모든 데이터 수집 후 디스코드로 딱 한 번 전송
        report_msg += "==========================================\n"
        report_msg += f"🕒 분석 시각: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        requests.post(DISCORD_WEBHOOK_URL, json={"content": report_msg})
        print("🚀 최종 리포트 전송 성공!")

    except Exception as e:
        print(f"❌ 전체 프로세스 오류: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
