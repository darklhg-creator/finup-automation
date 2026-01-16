import requests
import FinanceDataReader as fdr
import pandas as pd
import os
import time

# 디스코드 웹훅 설정
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_financial_growth(code):
    """네이버 금융에서 영업이익 성장 여부 확인 (25.12 vs 25.09)"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        tables = pd.read_html(res.text)
        finance_df = tables[3]
        finance_df.columns = finance_df.columns.get_level_values(1)
        finance_df.set_index('주요재무정보', inplace=True)
        
        op_profit = finance_df.loc['영업이익']
        # 날짜 컬럼 찾기 (예상치 E 포함)
        curr_q = [c for c in finance_df.columns if '2025.12' in c][0]
        prev_q = [c for c in finance_df.columns if '2025.09' in c][0]
        
        v_curr = float(op_profit[curr_q])
        v_prev = float(op_profit[prev_q])
        
        if pd.notna(v_curr) and pd.notna(v_prev) and v_curr > v_prev:
            return True, v_curr, v_prev
        return False, v_curr, v_prev
    except:
        return False, 0, 0

def main():
    print("🔍 1단계: 이격도 분석 시작...")
    df_krx = fdr.StockListing('KRX')
    df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
    
    # --- [1단계: 이격도 필터링] ---
    all_candidates = []
    for i, row in df_top500.iterrows():
        try:
            df = fdr.DataReader(row['Code']).tail(25)
            curr_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disparity = (curr_price / ma20) * 100
            all_candidates.append({'name': row['Name'], 'code': row['Code'], 'disp': disparity})
        except: continue

    u90 = [s for s in all_candidates if s['disp'] <= 90]
    u95 = [s for s in all_candidates if s['disp'] <= 95]
    step1_list = u90 if u90 else u95
    label = "90 이하" if u90 else "95 이하"

    # 1차 전송
    msg1 = f"📢 **[1단계] 이격도 {label} 종목 ({len(step1_list)}개)**\n"
    msg1 += "\n".join([f"· {s['name']}({s['code']}): {s['disp']:.1f}" for s in step1_list[:25]])
    requests.post(DISCORD_WEBHOOK_URL, data={'content': msg1})

    # --- [2단계: 재무 필터링] ---
    print("🔍 2단계: 재무 분석 시작...")
    step2_list = []
    for s in step1_list:
        is_growth, v1, v2 = get_financial_growth(s['code'])
        if is_growth:
            step2_list.append({'name': s['name'], 'code': s['code'], 'v_curr': v1, 'v_prev': v2})
        time.sleep(0.1)

    # 2차 전송
    msg2 = f"📊 **[2단계] 실적 성장 필터 완료 ({len(step2_list)}개)**\n"
    msg2 += "\n".join([f"· {s['name']}: {s['v_prev']:.0;f}억 → {s['v_curr']:.0;f}억" for s in step2_list]) if step2_list else "조건 부합 종목 없음"
    requests.post(DISCORD_WEBHOOK_URL, data={'content': msg2})

    # --- [3단계: 수급/뉴스 분석] ---
    # 여기에 아까 만든 수급/뉴스 로직을 step2_list 대상으로 실행...
