import FinanceDataReader as fdr
import pandas as pd
import requests
import os
import re
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_company_summary(code):
    """네이버 금융에서 기업 개요 한 줄 요약을 가져옴"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        # 'h4' 태그 중 'summary' 관련 내용을 찾거나, description 메타 태그 활용
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'lxml')
        summary_tag = soup.select_one('.summary_info')
        if summary_tag:
            # 첫 번째 문장이나 핵심 내용만 추출
            text = summary_tag.get_text(separator=' ').strip()
            # 너무 길면 자름 (한 줄 요약)
            summary = text.split('\n')[0][:100]
            return summary
        else:
            return "기업 정보 요약을 찾을 수 없습니다."
    except:
        return "정보 로딩 실패"

def get_disparity_stocks(codes, names, threshold):
    """특정 이격도 수치(threshold) 이하인 종목 리스트와 요약 반환"""
    results = []
    found_any = False
    for i, code in enumerate(codes):
        try:
            df = fdr.DataReader(code).tail(25)
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
    # 1. 휴장일 체크
    try:
        check_df = fdr.DataReader('005930', datetime.now().strftime('%Y%m%d'))
        if check_df.empty:
            requests.post(DISCORD_WEBHOOK_URL, data={'content': "🏝️ 오늘은 주식시장 휴장일입니다. 프로그램을 종료합니다."})
            return
    except:
        return

    print("🔍 1단계 분석 시작 (이격도 90 -> 95)")
    df_krx = fdr.StockListing('KRX')
    df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
    codes, names = df_top500['Code'].tolist(), df_top500['Name'].tolist()

    # 1차 시도: 90 이하
    under_stocks, success = get_disparity_stocks(codes, names, 90)
    current_threshold = 90

    # 2차 시도: 95 이하 (90이 없을 경우)
    if not success:
        print("💡 90 이하 없음, 95로 확장 중...")
        under_stocks, success = get_disparity_stocks(codes, names, 95)
        current_threshold = 95

    # 결과 전송
    if success:
        # 2단계를 위해 코드와 이름만 있는 파일 따로 저장
        with open("targets.txt", "w", encoding="utf-8") as f:
            # 파일에는 나중에 검색하기 편하게 코드,이름 형식으로 저장
            clean_list = [re.sub(r'[^0-9a-zA-Z가-힣,]', '', s.split(':')[0]) for s in under_stocks]
            f.write("\n".join(clean_list))
        
        msg = f"✅ **1단계 완료 (기준: 이격도 {current_threshold}이하)**\n\n" + "\n".join(under_stocks)
        requests.post(DISCORD_WEBHOOK_URL, data={'content': msg})
    else:
        if os.path.exists("targets.txt"): os.remove("targets.txt")
        requests.post(DISCORD_WEBHOOK_URL, data={'content': f"ℹ️ 오늘은 이격도 95 이하인 종목도 없습니다."})

if __name__ == "__main__":
    main()
