import FinanceDataReader as fdr
import pandas as pd
import requests
import os
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

# 깃허브 시크릿에서 디스코드 주소 가져오기
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_company_summary(code):
    """네이버 금융에서 기업 한 줄 요약을 가져오는 함수"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'lxml')
        summary_tag = soup.select_one('.summary_info')
        if summary_tag:
            text = summary_tag.get_text(separator=' ').strip()
            summary = text.split('\n')[0][:100] # 첫 줄만 추출
            return summary
        return "기업 정보 요약을 찾을 수 없습니다."
    except:
        return "정보 로딩 실패"

def get_disparity_stocks(codes, names, threshold):
    """설정한 이격도(threshold) 이하 종목을 찾는 함수"""
    results = []
    found_any = False
    for i, code in enumerate(codes):
        try:
            # 최근 25일치 데이터 수집
            df = fdr.DataReader(code).tail(25)
            if len(df) < 20: continue # 데이터 부족 시 패스
            
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
    # --- [Step 0] 휴장일 입구 컷 (가장 먼저 실행) ---
    print("📅 [검사] 오늘 시장이 열렸는지 확인합니다...")
    now_str = datetime.now().strftime('%Y%m%d')
    
    try:
        # 오늘 날짜의 삼성전자 데이터가 있는지 딱 확인
        check_df = fdr.DataReader('005930', now_str, now_str)
        
        if check_df.empty:
            print("🏝️ 오늘은 휴장일입니다. 메시지를 보냅니다.")
            msg = f"🏝️ 오늘은 주식시장 휴장일({
