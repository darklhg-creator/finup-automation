import requests
import pandas as pd
import os

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def check_growth(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        tables = pd.read_html(res.text)
        df = tables[3]
        df.columns = df.columns.get_level_values(1)
        df.set_index('주요재무정보', inplace=True)
        
        row = df.loc['영업이익']
        # 최근 분기 데이터 비교 (결측치 대비 float 변환)
        prev_q = float(row.iloc[7])
        curr_q = float(row.iloc[8])
        
        return (curr_q > prev_q, prev_q, curr_q)
    except Exception as e:
        return (False, 0, 0)

def main():
    # 파일명 확인 (start.py와 동일하게 targets.txt로 설정) 📍
    target_file = "targets.txt"
    
    if not os.path.exists(target_file):
        requests.post(DISCORD_WEBHOOK_URL, json={'content': "ℹ️ 1단계 분석 파일(targets.txt)이 없어 2단계를 건너뜁니다."})
        return
    
    with open(target_file, "r", encoding="utf-8") as f:
        targets = f.read().splitlines()

    if not targets:
        requests.post(DISCORD_WEBHOOK_URL, json={'content': "ℹ️ 분석할 후보 종목이 없습니다."})
        return

    final_results = []
    for line in targets:
        if "," not in line: continue
        
        # '코드,이름' 분리 📍
        code, name = line.split(",")
        is_up, v1, v2 = check_growth(code)
        
        if is_up:
            final_results.append(f"· **{name}**({code}): {v1:.0f}억 → {v2:.0f}억 📈")

    if final_results:
        msg = "🏆 **[2단계 필터 통과] 실적 성장 과매도주**\n\n" + "\n".join(final_results)
    else:
        msg = "📊 **[2단계 결과]** 영업이익 상승 조건을 만족하는 종목이 없습니다. 🏝️"
        
    requests.post(DISCORD_WEBHOOK_URL, json={'content': msg})

if __name__ == "__main__":
    main()
