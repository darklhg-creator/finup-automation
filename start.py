import FinanceDataReader as fdr
import pandas as pd
import requests
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_company_summary(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'lxml')
        summary_tag = soup.select_one('.summary_info')
        if summary_tag:
            text = summary_tag.get_text(separator=' ').strip()
            summary = text.split('\n')[0][:100]
            return summary
        return "기업 정보 요약을 찾을 수 없습니다."
    except:
        return "정보 로딩 실패"

def get_disparity_stocks(codes, names, threshold):
    results = []
    found_any = False
    for i, code in enumerate(codes):
        try:
            df = fdr.DataReader(code).tail(25)
            if len(df) < 20: continue
            curr = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disp = (curr / ma20) * 100
            if disp <= threshold:
                summary = get_company_summary(code)
                results.append(f"· **{names[i]}**({code}): {summary}")
                found_any = True
        except: continue
    return results, found_any

def main():
    print("🧪 [테스트] 휴장일 체크 없이 핀업까지 강제 진행합니다.")
    
    # 분석 시작 (테스트를 위해 삼성전자 하나만이라도 명단에 넣기)
    with open("targets.txt", "w", encoding="utf-8") as f:
        f.write("005930,삼성전자")
    
    requests.post(DISCORD_WEBHOOK_URL, data={'content': "🛠️ 테스트 모드: 핀업 리포트를 불러오기 위해 1단계를 강제 통과합니다."})

if __name__ == "__main__":
    main()
