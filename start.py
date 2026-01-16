import requests
import FinanceDataReader as fdr
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import time
import os
from datetime import datetime, timedelta

DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')

def get_oversold_stocks():
    # 오늘 날짜와 분석 시작일 설정
    now = datetime.now()
    start_date = (now - timedelta(days=60)).strftime('%Y-%m-%d')
    end_date = now.strftime('%Y-%m-%d')
    
    print(f"{end_date} 기준 시총 상위 1,000위 분석 시작...")
    
    try:
        df_krx = fdr.StockListing('KRX')
        df_top1000 = df_krx.sort_values(by='Marcap', ascending=False).head(1000)
        target_codes = df_top1000['Code'].tolist()
        target_names = df_top1000['Name'].tolist()
        
        all_stocks_data = []
        
        for i, code in enumerate(target_codes):
            try:
                # 기간을 명시적으로 지정하여 데이터 호출
                df = fdr.DataReader(code, start=start_date, end=end_date)
                if len(df) < 20: continue
                
                # 20일 이동평균선 (가장 최근 데이터 기준)
                ma20 = df['Close'].rolling(window=20).mean()
                current_price = df['Close'].iloc[-1]
                current_ma20 = ma20.iloc[-1]
                disparity = (current_price / current_ma20) * 100
                
                all_stocks_data.append({
                    'name': target_names[i],
                    'code': code,
                    'disparity': disparity
                })
            except:
                continue
        
        # 필터링
        under_90 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data if s['disparity'] <= 90]
        
        if under_90:
            return "🎯 [1차 필터: 이격도 90 이하]", under_90
        else:
            under_95 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data if s['disparity'] <= 95]
            # 만약 95 이하도 없다면 상위 5개라도 보여줘서 작동 여부 확인
            if not under_95:
                all_stocks_data.sort(key=lambda x: x['disparity'])
                lowest_5 = [f"· {s['name']}({s['code']}): {s['disparity']:.1f}" for s in all_stocks_data[:5]]
                return "❓ [조건 미달: 가장 이격도 낮은 종목 5개]", lowest_5
            return "🔍 [2차 필터: 이격도 95 이하]", under_95

    except Exception as e:
        return f"⚠️ 에러: {str(e)}", []

# 나머지 main 함수는 동일하게 유지
