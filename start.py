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
    print("📅 [검사] 오늘 시장 개장 여부를 확인합니다...")
    now = datetime.now()
    
    # 1. 요일 체크 (토요일=5, 일요일=6)
    if now.weekday() >= 5:
        print("🏝️ 오늘은 주말입니다. 종료합니다.")
        # 주말에는 메시지를 안 보내고 싶으시면 아래 줄을 주석 처리 하세요.
        requests.post(DISCORD_WEBHOOK_URL, data={'content': f"🏝️ 오늘은 즐거운 주말({now.strftime('%Y-%m-%d')})입니다. 비서는 쉬러 갑니다!"})
        return

    # 2. 공휴일/휴장일 체크 (삼성전자 데이터가 아예 안 올라오는 경우)
    now_str = now.strftime('%Y%m%d')
    try:
        # 최근 3일치 데이터를 가져와서 마지막 데이터 날짜가 오늘인지 확인
        check_df = fdr.DataReader('005930').tail(1)
        last_date = check_df.index[-1].strftime('%Y%m%d')
        
        # 마지막 거래일이 오늘이 아니라면 (장이 아직 안 열렸거나 휴장일인 경우)
        if last_date != now_str:
            print(f"🏝️ 마지막 거래일({last_date})이 오늘({now_str})과 다릅니다. 휴장일로 판단합니다.")
            requests.post(DISCORD_WEBHOOK_URL, data={'content': f"🏝️ 오늘은 시장 휴장일입니다. (마지막 거래일: {last_date})"})
            return
    except Exception as e:
        print(f"체크 중 오류: {e}")
        return

    # --- [Step 1] 개장일인 경우에만 아래 실행 ---
    print("🔍 분석 시작...")
    df_krx = fdr.StockListing('KRX')
    df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
    codes, names = df_top500['Code'].tolist(), df_top500['Name'].tolist()

    under_stocks, success = get_disparity_stocks(codes, names, 90)
    current_threshold = 90

    if not success:
        under_stocks, success = get_disparity_stocks(codes, names, 95)
        current_threshold = 95

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
        requests.post(DISCORD_WEBHOOK_URL, data={'content': "ℹ️ 오늘은 조건에 맞는 종목이 없습니다."})

if __name__ == "__main__":
    main()
