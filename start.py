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
            # 25일치 데이터를 한 번에 가져와서 계산
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
    print("📅 [검사] 오늘 시장이 열렸는지 확인합니다...")
    now_str = datetime.now().strftime('%Y%m%d')
    
    # ⚡ [초고속 판별] 500위 훑기 전에 삼성전자 데이터로 먼저 체크!
    try:
        check_df = fdr.DataReader('005930', now_str, now_str)
        if check_df.empty:
            print("🏝️ 휴장일 확인 완료. 메시지를 전송합니다.")
            requests.post(DISCORD_WEBHOOK_URL, data={'content': f"🏝️ 오늘은 주식시장 휴장일({datetime.now().strftime('%Y-%m-%d')})입니다. 비서는 이만 퇴근합니다!"})
            return
    except Exception as e:
        print(f"오류 발생: {e}")
        return

    # --- 여기서부터는 장이 열린 날에만 실행 (오래 걸리는 작업) ---
    print("🔍 1단계 분석 시작 (이격도 90 -> 95)")
    df_krx = fdr.StockListing('KRX')
    df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
    codes, names = df_top500['Code'].tolist(), df_top500['Name'].tolist()

    under_stocks, success = get_disparity_stocks(codes, names, 90)
    current_threshold = 90

    if not success:
        print("💡 90 이하 없음, 95로 확장 중...")
        under_stocks, success = get_disparity_stocks(codes, names, 95)
        current_threshold = 95

    if success:
        with open("targets.txt", "w", encoding="utf-8") as f:
            clean_list = [re.sub(r'[^0-9a-zA-Z가-힣,]', '', s.split(':')[0]) for s in under_stocks]
            f.write("\n".join(clean_list))
        
        msg = f"✅ **1단계 완료 (기준: 이격도 {current_threshold}이하)**\n\n" + "\n".join(under_stocks)
        requests.post(DISCORD_WEBHOOK_URL, data={'content': msg})
    else:
        if os.path.exists("targets.txt"): os.remove("targets.txt")
        requests.post(DISCORD_WEBHOOK_URL, data={'content': f"ℹ️ 오늘은 이격도 95 이하인 종목도 없습니다."})

if __name__ == "__main__":
    main()
