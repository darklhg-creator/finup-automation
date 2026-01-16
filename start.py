import FinanceDataReader as fdr
import pandas as pd
import requests
import os
import re
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
            summary = text.split('\n')[0][:100]
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
    # --- [Step 0] 휴장일 입구 컷 ---
    print("📅 [검사] 오늘 시장이 열렸는지 확인합니다...")
    now_str = datetime.now().strftime('%Y%m%d')
    
    try:
        check_df = fdr.DataReader('005930', now_str, now_str)
        if check_df.empty:
            print("🏝️ 오늘은 휴장일입니다. 메시지를 보냅니다.")
            msg = f"🏝️ 오늘은 주식시장 휴장일({datetime.now().strftime('%Y-%m-%d')})입니다. 비서는 이만 퇴근합니다!"
            requests.post(DISCORD_WEBHOOK_URL, data={'content': msg})
            return
    except:
        return

    # --- [Step 1] 장이 열린 날 분석 ---
    print("🔍 분석 시작 (이격도 90 -> 95)")
    df_krx = fdr.StockListing('KRX')
    df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
    codes, names = df_top500['Code'].tolist(), df_top500['Name'].tolist()

    # 1차 시도: 90 이하
    under_stocks, success = get_disparity_stocks(codes, names, 90)
    current_threshold = 90

    # 2차 시도: 95 확장
    if not success:
        print("💡 95로 확장 분석 중...")
        under_stocks, success = get_disparity_stocks(codes, names, 95)
        current_threshold = 95

    # --- [Step 2] 결과 보고 ---
    if success:
        with open("targets.txt", "w", encoding="utf-8") as f:
            clean_list = []
            for item in under_stocks:
                match = re.search(r'\*\*(.*?)\*\*\((\d+)\)', item)
                if match:
                    name, code = match.groups()
                    clean_list.append(f"{code},{name}")
            f.write("\n".join(clean_list))
        
        report_msg = f"✅ **1단계 완료 (기준: 이격도 {current_threshold}이하)**\n\n" + "\n".join(under_stocks)
        requests.post(DISCORD_WEBHOOK_URL, data={'content': report_msg})
    else:
        if os.path.exists("targets.txt"): os.remove("targets.txt")
        requests.post(DISCORD_WEBHOOK_URL, data={'content': "ℹ️ 오늘은 이격도 95 이하인 종목도 없습니다."})

if __name__ == "__main__":
    main()
