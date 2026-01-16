import requests
import FinanceDataReader as fdr
import pandas as pd
import os

# 디스코드 웹훅 설정
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_oversold_stocks():
    print("🔍 통합 시총 상위 500위 분석 시작...")
    try:
        # 1. 시총 상위 500위 추출
        df_krx = fdr.StockListing('KRX')
        df_top500 = df_krx.sort_values(by='Marcap', ascending=False).head(500)
        target_codes = df_top500['Code'].tolist()
        target_names = df_top500['Name'].tolist()
        
        all_stocks_data = []
        
        # 2. 데이터 수집 및 이격도 계산
        for i, code in enumerate(target_codes):
            try:
                df = fdr.DataReader(code).tail(25)
                if len(df) < 20: continue
                
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                disparity = (current_price / ma20) * 100
                
                all_stocks_data.append({'name': target_names[i], 'code': code, 'disparity': disparity})
                if (i + 1) % 100 == 0: print(f"✅ {i+1}/500 완료")
            except:
                continue
        
        # 3. 우선순위 필터링 로직 (90% 이하 -> 없으면 95% 이하)
        under_90 = [s for s in all_stocks_data if s['disparity'] <= 90]
        under_95 = [s for s in all_stocks_data if s['disparity'] <= 95]
        
        if under_90:
            title = "🚨 [긴급] 이격도 90 이하 과매도 종목"
            selected_stocks = sorted(under_90, key=lambda x: x['disparity'])
        elif under_95:
            title = "⚠️ [주의] 이격도 95 이하 관심 종목"
            selected_stocks = sorted(under_95, key=lambda x: x['disparity'])
        else:
            title = "ℹ️ 이격도 최하위 5종목 (95 초과)"
            selected_stocks = sorted(all_stocks_data, key=lambda x: x['disparity'])[:5]
            
        return title, [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in selected_stocks]

    except Exception as e:
        return f"❌ 에러 발생: {str(e)}", []

def main():
    title_text, stock_list = get_oversold_stocks()
    
    # 메시지 구성 (최대 25개까지만 출력)
    stock_msg = "\n".join(stock_list[:25])
    content = f"📈 **주식 장 종료 보고서**\n\n**{title_text}**\n{stock_msg}"
    
    # 디스코드 전송 (파일 없이 텍스트만 전송)
    requests.post(DISCORD_WEBHOOK_URL, data={'content': content})
    print(f"🏁 분석 완료 및 전송 성공: {title_text}")

if __name__ == "__main__":
    main()
