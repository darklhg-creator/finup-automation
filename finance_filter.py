import FinanceDataReader as fdr
import pandas as pd
import requests
import os

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def check_profit_growth(code):
    """네이버 금융에서 분기 영업이익 성장세 확인"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        tables = pd.read_html(requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text)
        df = tables[3]
        df.columns = df.columns.get_level_values(1)
        df.set_index('주요재무정보', inplace=True)
        
        # 영업이익 행 추출
        op_profit = df.loc['영업이익']
        # 최근 분기(25.12)와 이전 분기(25.09) 데이터 비교 (연도는 상황에 따라 자동매칭)
        # 값이 숫자인지 확인하고 증가했으면 True 반환
        if float(op_profit.iloc[8]) > float(op_profit.iloc[7]): # 7번째, 8번째 컬럼이 분기 데이터
            return True, op_profit.iloc[7], op_profit.iloc[8]
        return False, 0, 0
    except:
        return False, 0, 0

def main():
    # 실제로는 start.py에서 넘겨받은 리스트를 써야 하지만, 
    # 독립 실행 테스트를 위해 상위 종목 중 이격도 낮은 것들을 임시로 가정합니다.
    print("📊 2단계: 재무 필터링 시작 (영업이익 성장주 찾기)")
    
    # 예시 종목 (나중에는 start.py의 결과를 파일로 읽어오게 수정 가능)
    target_stocks = [{"name": "삼성전자", "code": "005930"}] 
    
    final_list = []
    for stock in target_stocks:
        growth, p_val, c_val = check_profit_growth(stock['code'])
        if growth:
            final_list.append(f"✅ {stock['name']}: {p_val}억 -> {c_val}억 (상승)")

    if final_list:
        msg = "🏆 **[재무 필터 통과] 실적 성장 과매도주**\n" + "\n".join(final_list)
        requests.post(DISCORD_WEBHOOK_URL, data={'content': msg})
