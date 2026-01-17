import FinanceDataReader as fdr
import requests
import pandas as pd
import re

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def get_company_desc(code):
    """네이버 금융에서 기업 개요를 가져오는 함수 (설명 누락 방지)"""
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers={'User-agent': 'Mozilla/5.0'})
        # 섹터나 주요 제품 정보를 정규식으로 간단히 추출
        match = re.search(r'summary">.*?<em>(.*?)</em>', res.text, re.DOTALL)
        if match:
            return match.group(1).strip()
    except:
        pass
    return "사업 정보 확인 중"

def get_analysis(target_stocks, threshold):
    results = []
    for idx, row in target_stocks.iterrows():
        try:
            name = row['Name']
            code = row['Code']
            
            # 주가 데이터 분석
            df = fdr.DataReader(code).tail(30)
            if len(df) < 20: continue
            
            current_price = df['Close'].iloc[-1]
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
            disparity = round((current_price / ma20) * 100, 1)

            if disparity <= threshold:
                # 설명이 없으면 직접 가져오기 시도
                desc = row.get('Sector', row.get('Industry', ''))
                if not desc or pd.isna(desc) or desc == "사업 정보 없음":
                    desc = get_company_desc(code)
                
                results.append({'name': name, 'code': code, 'disparity': disparity, 'desc': desc})
        except:
            continue
    return results

def main():
    print("🚀 [1단계 분석] 어제 리스트 포함을 위해 범위를 확장하여 분석 시작...")
    
    try:
        # 어제 종목들이 포함되도록 범위를 각 1000개로 확장
        df_kospi = fdr.StockListing('KOSPI').head(1000)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(1000)
        target_stocks = pd.concat([df_kospi, df_kosdaq])
    except:
        return

    # 1차 90 이하 -> 2차 95 이하 순차 검색
    final_results = get_analysis(target_stocks, 90)
    search_range = "90 이하"
    if not final_results:
        final_results = get_analysis(target_stocks, 95)
        search_range = "95 이하"

    if final_results:
        final_results = sorted(final_results, key=lambda x: x['disparity'])
        
        # 어제와 같은 양식: 종목명(코드): 이격도 - 설명
        report = f"### 📊 1단계 분석 ({search_range})\n"
        for r in final_results:
            report += f"· **{r['name']}({r['code']})**: {r['disparity']}\n"
            report += f"  └ {r['desc'][:60]}\n\n"
        
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
        
        with open("filtered_targets.txt", "w", encoding="utf-8") as f:
            f.write("\n".join([r['name'] for r in final_results]))
        print(f"✅ 분석 완료! {len(final_results)}종목 전송")

if __name__ == "__main__":
    main()
