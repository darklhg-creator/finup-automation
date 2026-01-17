import FinanceDataReader as fdr
import pandas as pd
import requests
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

# 이격도 채널 전용 웹훅
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

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
        return "기업 정보 요약 없음"
    except:
        return "정보 로딩 실패"

def get_disparity_stocks(stocks_dict, threshold):
    results = []
    found_any = False
    
    for name, code in stocks_dict.items():
        try:
            # 주가 데이터 수집 (최근 25거래일)
            df = fdr.DataReader(code).tail(25)
            if len(df) < 20: continue
            
            curr = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disp = (curr / ma20) * 100
            
            # 이격도 필터링 (threshold 이하)
            if disp <= threshold:
                summary = get_company_summary(code)
                results.append(f"· **{name}**({code}) - 이격도: **{disp:.2f}**\n  > {summary}")
                found_any = True
        except:
            continue
            
    return results, found_any

def main():
    print("📊 [실전 모드] 이격도 분석 및 채널 전송 시작...")
    
    # 1. pinup.py로부터 넘어온 종목 리스트 읽기
    stocks_to_check = {}
    if os.path.exists("targets.txt"):
        with open("targets.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # 종목코드 추출 시도 (FDR 활용)
                try:
                    # pinup.py에서 '삼성전자'만 넘겨줄 경우 코드를 찾는 로직
                    # (성능을 위해 pinup.py에서 '005930,삼성전자' 형태로 저장하는 것이 가장 좋음)
                    if ',' in line:
                        code, name = line.split(',')
                        stocks_to_check[name] = code
                    else:
                        # 종목명만 있을 경우 임시 처리 (필요시 KRX 리스트 로드하여 매칭)
                        print(f"⚠️ {line}의 코드가 없어 건너뜁니다. (pinup.py 수정 필요)")
                except:
                    continue

    if not stocks_to_check:
        print("ℹ️ 분석할 실전 데이터가 없습니다. (targets.txt 확인 필요)")
        return

    # 2. 1순위: 이격도 90 이하 탐색
    final_list, found = get_disparity_stocks(stocks_to_check, 90)
    
    # 3. 2순위: 90 이하가 없으면 95 이하 탐색
    if not found:
        print("💡 이격도 90 이하 종목 없음. 95 이하 재탐색...")
        final_list, found = get_disparity_stocks(stocks_to_check, 95)

    # 4. 결과 전송 (이격도 채널)
    if found:
        msg = f"📉 **오늘의 이격도 과매도 구간 종목 (실전)**\n" + "\n".join(final_list)
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': msg})
        print("✅ 이격도 채널 전송 완료")
    else:
        print("ℹ️ 조건에 맞는 종목이 없습니다.")

if __name__ == "__main__":
    main()
