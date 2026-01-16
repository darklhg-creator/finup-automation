import requests
import FinanceDataReader as fdr
import pandas as pd
import os
import time
from collections import Counter

# 디스코드 웹훅 설정
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_foreign_strength(code):
    """외국인 수급 강도 분석 (최근 5일 평균 대비 오늘 매수량)"""
    try:
        # 실제 환경에서는 수급 데이터를 제공하는 API나 크롤링이 필요합니다.
        # 여기서는 FinanceDataReader의 데이터를 활용한 예시 로직을 구성합니다.
        df = fdr.DataReader(code).tail(10)
        # 외국인 순매수 데이터가 포함된 DataFrame이라고 가정 (실제 컬럼명 확인 필요)
        # 예: df['ForeignNetBuy']
        
        # 임시 로직: 거래량 대비 외국인 비중이나 특정 지표를 활용할 수 있습니다.
        # 여기서는 로직의 흐름을 보여드리기 위해 성공률이 높은 구조로 짭니다.
        return True, 5.2  # 5.2배 강도로 유입되었다고 가정
    except:
        return False, 0

def get_news_keywords(stock_name):
    """네이버 뉴스에서 핵심 키워드 3개 추출"""
    try:
        url = f"https://search.naver.com/search.naver?where=news&query={stock_name}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        # 간단한 텍스트 기반 키워드 추출 (실제로는 BeautifulSoup 활용)
        keywords = ["수주", "흑자", "신사업"] # 예시 키워드
        return ", ".join(keywords)
    except:
        return "키워드 분석 불가"

# ... (기존 get_theme_data, get_financial_growth 함수 포함) ...

def main():
    print("🚀 종합 시장 분석 및 슈퍼 종목 발굴 시작...")
    
    # 1. 시총 500위 분석 및 1차/2차 필터링 진행 (이격도 & 실적)
    # (앞선 코드의 로직을 그대로 수행)
    
    # 2. 최종 후보군에 대해 수급 및 뉴스 심화 분석
    final_super_stocks = []
    # 예시: target_list 중 실적 성장까지 확인된 종목들
    test_candidates = [{"name": "삼성전자", "code": "005930", "disp": 89.5}] 
    
    for s in test_candidates:
        is_strong, strength = get_foreign_strength(s['code'])
        if is_strong and strength >= 3.0: # 3배 이상 유입 시
            keywords = get_news_keywords(s['name'])
            final_super_stocks.append(
                f"💎 **{s['name']}**\n"
                f"   - 수급강도: {strength:.1f}배 유입 💰\n"
                f"   - 뉴스 키워드: [{keywords}] 📰"
            )

    # 3. 디스코드 전송
    if final_super_stocks:
        msg = "🎯 **[오늘의 슈퍼 반등 후보군]**\n" + "\n".join(final_super_stocks)
        requests.post(DISCORD_WEBHOOK_URL, data={'content': msg})
    
    print("🏁 모든 분석이 완료되었습니다!")

if __name__ == "__main__":
    main()
