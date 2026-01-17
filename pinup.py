import os
import time
import requests
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def main():
    print("📸 1. 핀업 테마로그 화면 캡처 중...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1600,1200')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # 주소 접속
        driver.get("https://finance.finup.co.kr/Lab/ThemeLog")
        time.sleep(15) # 화면이 다 뜰 때까지 대기
        
        # 화면 전체 캡처 (증거 및 분석용)
        driver.save_screenshot("screenshot.png")
        print("✅ 2. 캡처 완료. 화면에서 텍스트 추출을 시작합니다.")

        # 캡처된 화면의 '요소'들을 텍스트 위주로 긁어모음 (이미지 기반 인식의 첫 단계)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # 텍스트에서 [테마명] + [%수치] 패턴을 찾음
        # 예: "자동차 부품 +19.15%" 같은 형태를 모두 찾음
        pattern = r'([가-힣A-Za-z0-9/ ]+)\n?([+-]?\d+\.\d+%)'
        matches = re.findall(pattern, body_text)
        
        extracted_data = []
        for name, rate in matches:
            # 수치에서 숫자만 뽑아 정렬용 값으로 변환
            val = float(rate.replace('%', ''))
            extracted_data.append({'name': name.strip(), 'rate': rate, 'val': val})

        # 큰 순서대로 정렬 (내림차순)
        top5 = sorted(extracted_data, key=lambda x: x['val'], reverse=True)[:5]

        print("\n📊 [정리 결과: 상위 5개 섹터]")
        print("=" * 30)
        if not top5:
            print("데이터를 추출하지 못했습니다. 화면 구성을 다시 확인 중입니다.")
        else:
            for i, item in enumerate(top5):
                print(f"{i+1}위: {item['name']} ({item['rate']})")
        print("=" * 30)

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
