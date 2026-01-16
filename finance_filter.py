import requests
import pandas as pd
import os

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def check_growth(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        # 네이버 금융 재무제표 테이블 추출
        tables = pd.read_html(res.text)
        df = tables[3]
        df.columns = df.columns.get_level_values(1)
        df.set_index('주요재무정보', inplace=True)
        
        # 영업이익 행에서 최근 두 분기 데이터 비교
        row = df.loc['영업이익']
        # iloc[7]은 전전분기, iloc[8]은 전분기 데이터입니다.
        prev_q = float(row.iloc[7])
        curr_q = float(row.iloc[8])
        
        return (curr_q > prev_q, prev_q, curr_q)
    except Exception as e:
        print(f"Error checking {code}: {e}")
        return (False, 0, 0)

def main():
    # 1단계에서 만든 파일이 있는지 확인
    if not os.path.exists("targets.txt"):
        requests.post(DISCORD_WEBHOOK_URL, data={'content': "ℹ️ 1단계 분석 파일이 없어 2단계를 건너뜁니다."})
        return
    
    with open("targets.txt", "r", encoding="utf-8") as f:
        targets = f.read().splitlines()

    if not targets:
        requests.post(DISCORD_WEBHOOK_URL, data={'content': "ℹ️ 1단계에서 추출된 후보 종목이 없습니다."})
        return

    final_results = []
    for line in targets:
        if "," not in line: continue
        code, name = line.split(",")
        is_up, v1, v2 = check_growth(code)
        if is_up:
            final_results.append(f"· **{name}**({code}): {v1:.0f}억 → {v2:.0f}억 📈")

    # 결과 전송 로직
    if final_results:
        msg = "🏆 **[2단계 필터 통과] 실적 성장 과매도주**\n\n" + "\n".join(final_results)
    else:
        msg = "📊 **[2단계 결과]** 이격도 종목 중 '영업이익 상승' 조건을 만족하는 종목이 오늘 장에는 없습니다. 🏝️"
        
    requests.post(DISCORD_WEBHOOK_URL, data={'content': msg})

if __name__ == "__main__":
    main()
