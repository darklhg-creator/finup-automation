import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def main():
    print("🔍 핀업 히트맵에서 TOP 5 테마 추출 시작...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,1200')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 1. 대상 주소 접속
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) # 맵이 완전히 그려질 때까지 충분히 대기

        # 2. 히트맵 내의 모든 테마 블록 찾기
        # 이미지상 빨간색/파란색 박스들은 보통 특정 클래스를 공유합니다.
        # 텍스트와 숫자가 같이 들어있는 요소들을 수집합니다.
        themes = driver.find_elements(By.XPATH, "//*[contains(@class, 'item')] | //*[contains(@class, 'theme')]")
        
        extracted_data = []
        
        for theme in themes:
            try:
                # 박스 내부의 텍스트 전체를 가져옴 (예: "자동차 부품\n+19.15%")
                full_text = theme.text.strip()
                if '%' in full_text:
                    # 줄바꿈이나 공백으로 분리
                    lines = full_text.split('\n')
                    name = lines[0].strip()
                    rate_text = lines[1].strip() if len(lines) > 1 else lines[0]
                    
                    # 숫자만 추출 (정렬용)
                    rate_val = float(re.sub(r'[^0-9.-]', '', rate_text))
                    
                    # 중복 제거 및 유효한 이름만 저장
                    if name and len(name) < 15:
                        extracted_data.append({'name': name, 'rate': rate_text, 'val': rate_val})
            except:
                continue

        # 3. 수치(% )가 높은 순서대로 상위 5개 정렬
        # 중복 데이터 정제
        unique_data = {d['name']: d for d in extracted_data}.values()
        top5 = sorted(unique_data, key=lambda x: x['val'], reverse=True)[:5]

        print("\n🏆 [추출 결과 - TOP 5]")
        print("--------------------------------")
        for i, t in enumerate(top5):
            print(f"{i+1}위: {t['name']} ({t['rate']})")
        print("--------------------------------\n")

        # 확인용 스크린샷 저장
        driver.save_screenshot("map_check.png")
        print("📸 현재 맵 화면을 map_check.png로 저장했습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
