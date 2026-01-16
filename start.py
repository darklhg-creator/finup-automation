import requests
import FinanceDataReader as fdr
import pandas as pd
import os
import time

# 디스코드 웹훅 설정
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_foreign_buy_strength(code):
    """오늘 외국인 순매수량이 최근 5일 평균 대비 얼마나 강력한지 계산"""
    try:
        # 투자자별 매매동향 데이터를 가져옵니다 (데이터 소스에 따라 컬럼명 확인 필요)
        # fdr에서는 종목별 상세 수급을 위해 별도의 크롤링이나 API 연결이 권장됩니다.
        # 여기서는 로직 구현을 위해 평균 대비 비율을 계산하는 구조를 잡습니다.
        
        # 실제 운영시에는 네이버 금융의 '투자자별 매매동향' 표를 활용하는 것이 정확합니다.
        # 예시: 오늘 50만주 / 최근 5일 평균 10만주 = 5.0배
        strength = 4.5 # 테스트를 위한 가상 수치
        return True, strength
    except:
        return False, 0

def get_news_summary(stock_name):
    """네이버 뉴스 제목에서 주요 키워드 추출"""
    try:
        # 뉴스 제목들을 긁어와서 핵심 단어만 보여줍니다.
        # 실제 구현 시 BeautifulSoup을 사용해 뉴스 제목을 파싱합니다.
        return "수주 확대, 흑자 전환, 신기술 발표" 
    except:
        return "분석 중"

def main():
    print("📊 시장 종합 분석 시스템 가동...")
    
    # 1. 시총 500위 중 이격도 필터링
    df_krx = fdr.StockListing('KRX')
    df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
    
    # ... (중략: 이격도 및 영업이익 상승 로직 수행) ...
    # 최종 선별된 종목이 'candidate_stocks'라고 가정합니다.
    candidate_stocks = [{"name": "현대차", "code": "005380", "v_curr": 40000, "v_prev": 35000}]

    final_report = []
    for s in candidate_stocks:
        # 수급 분석
        is_strong, strength = get_foreign_buy_strength(s['code'])
        # 뉴스 분석
        news_keywords = get_news_summary(s['name'])
        
        # 리포트 구성
        report = (
            f"💎 **{s['name']}** ({s['code']})\n"
            f"   - **수급 강도: {strength:.1f}배 유입** (평균 대비) 💰\n"
            f"   - **실적: {s['v_prev']:,}억 → {s['v_curr']:,}억 (상승)** 📈\n"
            f"   - **최신 뉴스: [{news_keywords}]** 📰"
        )
        final_report.append(report)

    # 디스코드 전송
    if final_report:
        full_msg = "🎯 **[오늘의 슈퍼 반등 후보 종목]**\n\n" + "\n\n".join(final_report)
        requests.post(DISCORD_WEBHOOK_URL, data={'content': full_msg})
    
    print("🏁 분석 완료!")

if __name__ == "__main__":
    main()
