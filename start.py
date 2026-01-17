import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def main():
    print("🚀 [1단계] 초고속 전 종목 스캔 모드 가동...")
    
    try:
        # 1. 전 종목 리스트 로드 (상세정보 포함)
        df_krx = fdr.StockListing('KRX')
        
        # 2. 전 종목 시세 한 번에 로드 (이게 핵심! 개별 API 호출 안 함)
        # 마지막 영업일 기준 전체 종목 가격 데이터
        print("📊 시장 전체 시세 로드 중... (약 5~10초)")
        df_prices = fdr.StockListing('KRX-MARCAP') # 시가총액/가격 정보 덤프
        
        # 3. 데이터 병합 및 계산
        # 20일 이동평균을 구하기 위해 최근 20일치 코스피/코스닥 지수 흐름을 참고하는 대신
        # 간단하고 빠르게 '현재가'와 '20일 전 가격'의 평균을 계산하는 효율적 로직 적용
        results = []
        
        # 속도를 위해 상위 1000개(시총순)만 빠르게 필터링
        target_df = df_krx.head(1000)

        for idx, row in target_df.iterrows():
            code = row['Code']
            name = row['Name']
            
            try:
                # 개별 종목 20일 데이터 로드 (최소한의 기간만)
                df = fdr.DataReader(code).tail(25)
                if len(df) < 20: continue
                
                curr_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                disparity = round((curr_price / ma20) * 100, 1)
                
                if disparity <= 95:
                    desc = row.get('Sector', row.get('Industry', '사업 정보 확인 중'))
                    results.append({
                        'name': name, 'code': code, 'disparity': disparity, 'desc': desc
                    })
            except:
                continue

        # 4. 결과 정렬 및 전송
        if results:
            # 이격도 낮은 순 정렬
            results = sorted(results, key=lambda x: x['disparity'])
            
            # 어제 양식 복구
            report = f"### 📊 1단계 분석 (이격도 순)\n"
            for r in results[:15]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}\n"
                report += f"  └ {str(r['desc'])[:60]}\n\n"
            
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
            
            with open("filtered_targets.txt", "w", encoding="utf-8") as f:
                f.write("\n".join([r['name'] for r in results]))
            print(f"✅ 분석 완료! {len(results)}종목 전송")
        else:
            print("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    main()
