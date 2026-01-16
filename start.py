import requests
import FinanceDataReader as fdr
import pandas as pd
import os
import time

# 디스코드 웹훅 설정
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_financial_growth(code):
    """네이버 금융에서 영업이익 성장 여부 확인 (오류 시 패스)"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        # 헤더를 넣어 브라우저인 척 합니다
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        tables = pd.read_html(res.text)
        
        # 기업분석 재무제표 표 추출 (보통 3번째 표)
        finance_df = tables[3]
        finance_df.columns = finance_df.columns.get_level_values(1)
        finance_df.set_index('주요재무정보', inplace=True)
        
        # 영업이익 행 선택
        op_profit = finance_df.loc['영업이익']
        
        # 2025.12(당기)와 2025.09(전기) 데이터 추출
        # '2025.12(E)' 또는 '2025.12' 형태를 찾습니다
        curr_q = [c for c in finance_df.columns if '2025.12' in c][0]
        prev_q = [c for c in finance_df.columns if '2025.09' in c][0]
        
        v_curr = float(op_profit[curr_q])
        v_prev = float(op_profit[prev_q])
        
        # 당기 실적이 전기보다 높고, 데이터가 유효(NaN 아님)한지 확인
        if pd.notna(v_curr) and pd.notna(v_prev) and v_curr > v_prev:
            return True, v_curr, v_prev
        return False, 0, 0
    except:
        return False, 0, 0 # 오류 발생 시 조용히 패스

def main():
    print("🔍 1단계: 시총 500위 이격도 분석 시작...")
    df_krx = fdr.StockListing('KRX')
    df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
    
    candidates = []
    for i, row in df_top500.iterrows():
        try:
            df = fdr.DataReader(row['Code']).tail(25)
            curr_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disparity = (curr_price / ma20) * 100
            candidates.append({'name': row['Name'], 'code': row['Code'], 'disp': disparity})
        except: continue

    # 이격도 필터링 (90 우선, 없으면 95)
    u90 = [s for s in candidates if s['disp'] <= 90]
    u95 = [s for s in candidates if s['disp'] <= 95]
    
    target_list = u90 if u90 else u95
    status_label = "90 이하" if u90 else "95 이하"

    # 1차 결과 전송
    msg1 = f"📢 **[1차 필터] 이격도 {status_label} 종목 ({len(target_list)}개)**\n"
    msg1 += "\n".join([f"· {s['name']}({s['code']}): {s['disp']:.1f}" for s in target_list[:20]])
    requests.post(DISCORD_WEBHOOK_URL, data={'content': msg1})

    print("🔍 2단계: 영업이익 성장 분석 시작...")
    final_list = []
    for s in target_list:
        is_growth, v1, v2 = get_financial_growth(s['code'])
        if is_growth:
            final_list.append(f"· **{s['name']}**: {v2:.0f}억 → {v1:.0f}억 (↑)")
        time.sleep(0.1) # 서버 부하 방지

    # 2차 결과 전송
    msg2 = f"🏆 **[최종 필터] 실적 성장 중인 과매도주 ({len(final_list)}개)**\n"
    msg2 += "\n".join(final_list) if final_list else "조건에 맞는 종목이 없습니다."
    requests.post(DISCORD_WEBHOOK_URL, data={'content': msg2})
    print("🏁 모든 분석 완료!")

if __name__ == "__main__":
    main()
