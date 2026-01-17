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
    print("🧪 [테스트 모드] 휴장일 체크를 건너뛰고 분석을 강제 시작합니다.")
    
    # --- 아래 휴장일 체크 로직을 잠시 주석처리(#) 했습니다 ---
    # now = datetime.now()
    # if now.weekday() >= 5:
    #     return
    # --------------------------------------------------

    print("🔍 분석 시작 (테스트 중...)")
    df_krx = fdr.StockListing('KRX')
    df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
    codes, names = df_top500['Code'].tolist(), df_top500['Name'].tolist()

    # 테스트를 위해 이격도 기준을 100으로 높여서 종목이 무조건 걸리게 함 (선택 사항)
    under_stocks, success = get_disparity_stocks(codes, names, 95)

    if success:
        with open("targets.txt", "w", encoding="utf-8") as f:
            clean_list = []
            for item in under_stocks:
                match = re.search(r'\*\*(.*?)\*\*\((\d+)\)', item)
                if match:
                    name, code = match.groups()
                    clean_list.append(f"{code},{name}")
            f.write("\n".join(clean_list))
        
        report_msg = f"✅ **1단계 테스트 완료**\n\n" + "\n".join(under_stocks)
        requests.post(DISCORD_WEBHOOK_URL, data={'content': report_msg})
    else:
        # 종목이 없으면 테스트가 안되니 강제로 targets.txt 생성 (삼성전자)
        with open("targets.txt", "w", encoding="utf-8") as f:
            f.write("005930,삼성전자")
        requests.post(DISCORD_WEBHOOK_URL, data={'content': "ℹ️ 테스트 중: 조건 종목이 없어 삼성전자로 대체 진행합니다."})

if __name__ == "__main__":
    main()
