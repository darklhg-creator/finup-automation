import FinanceDataReader as fdr
import requests
import pandas as pd
from datetime import datetime
import time

IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

# --- [신규 추가] 테마 분석 및 하단 리포트 생성 함수 ---
def send_theme_analysis(results):
    """기존 분석 결과 아래에 테마별 분류와 요약을 추가로 전송합니다."""
    # 테마 사전 (매일 바뀌는 종목들을 분류하는 기준)
    theme_map = {
        "🚀 AI/반도체/유리기판": ["태성", "에스투더블유", "아이스크림미디어", "가온칩스"],
        "🧬 바이오/헬스케어": ["지아이이노베이션", "퓨쳐켐", "안트로젠", "엘앤씨바이오", "한스바이오메드", "프로티나", "젬백스", "큐리오시스"],
        "🔋 2차전지/리튬/소재": ["중앙첨단소재", "석경에이티", "엔켐"],
        "🌿 에너지/인프라/기타": ["유니슨", "대성산업", "글로벌텍스프리", "천일고속", "아세아", "우주일렉트로", "티엠씨"]
    }
    
    classified = {theme: [] for theme in theme_map.keys()}
    unclassified = []

    # 종목 분류 로직
    for r in results:
        name = r['name']
        found = False
        for theme, members in theme_map.items():
            if name in members:
                classified[theme].append(name)
                found = True
                break
        if not found:
            unclassified.append(name)

    # 리포트 생성
    report = "\n**🏷️ [추가 분석] 실시간 테마 분류 결과**\n"
    report += "--------------------------------------------\n"
    
    for theme, members in classified.items():
        if members:
            report += f"**[{theme}]**: {', '.join(members)}\n"
            
    if unclassified:
        # 미분류 종목이 너무 많으면 15개까지만 표시
        report += f"**[🔍 기타/신규]**: {', '.join(unclassified[:15])}\n"

    report += "--------------------------------------------\n"
    report += "💡 **요약 및 참고사항**\n"
    
    # 테마 비중 요약
    counts = {k: len(v) for k, v in classified.items()}
    top_theme = max(counts, key=counts.get)
    
    if counts[top_theme] > 0:
        report += f"- 오늘 포착된 종목 중 **{top_theme}** 섹터의 비중이 가장 높습니다.\n"
    
    if any(x['name'] == '태성' for x in results):
        report += "- **유리기판 대장주(태성)**가 과매도 구간에 포착되었습니다. 반등 시점을 주시하세요.\n"
    
    report += "- 테마주 특성상 급등락이 심하므로 기술적 반등 시 분할 매도로 대응하시기 바랍니다."

    # 기존 결과 아래로 전송
    requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})

# --- [기존 main 함수 그대로 유지] ---
def main():
    print("🚀 [1단계] 정밀 분석 시작 (KOSPI 500 + KOSDAQ 500)")
    
    try:
        # 휴장일 체크
        #check_df = fdr.DataReader('005930').tail(1)
        #last_date = check_df.index[-1].strftime('%Y-%m-%d')
        #today_date = datetime.now().strftime('%Y-%m-%d')

        #if last_date != today_date:
            #msg = f"📅 오늘은 주식 시장 휴무일입니다. ({today_date})"
            #print(msg)
            #requests.post(IGYEOK_WEBHOOK_URL, json={'content': msg})
            #return

        # 1. 대상 종목 선정
        df_kospi = fdr.StockListing('KOSPI').head(500)
        df_kosdaq = fdr.StockListing('KOSDAQ').head(500)
        df_total = pd.concat([df_kospi, df_kosdaq])
        
        results = []
        print(f"📡 총 {len(df_total)}개 종목 분석 중...")

        for idx, row in df_total.iterrows():
            code = row['Code']
            name = row['Name']
            
            try:
                df = fdr.DataReader(code).tail(30)
                if len(df) < 20: continue
                
                current_price = df['Close'].iloc[-1]
                ma20 = df['Close'].rolling(window=20).mean().iloc[-1]
                disparity = round((current_price / ma20) * 100, 1)

                if disparity <= 95:
                    results.append({'name': name, 'code': code, 'disparity': disparity})
            except:
                continue

        # 2. 결과 정렬 및 저장/전송
        if results:
            results = sorted(results, key=lambda x: x['disparity'])
            
            # [기존 로직] 디스코드 리포트 생성
            report = f"### 📊 1단계 정밀 분석 결과\n"
            for r in results[:20]:
                report += f"· **{r['name']}({r['code']})**: {r['disparity']}\n"
            
            # [기본 리포트 전송]
            requests.post(IGYEOK_WEBHOOK_URL, json={'content': report})
            
            # --- [여기서 신규 추가 함수 호출] ---
            # 기존 결과 전송 직후 아래에 테마 분석 리포트를 보냅니다.
            send_theme_analysis(results)
            # ------------------------------------
            
            # 2단계를 위해 '코드,종목명' 형식으로 targets.txt에 저장 📍
            with open("targets.txt", "w", encoding="utf-8") as f:
                lines = [f"{r['code']},{r['name']}" for r in results]
                f.write("\n".join(lines))
                
            print(f"✅ 분석 완료! 테마 리포트 전송 및 targets.txt 생성됨")
        else:
            print("🔍 조건에 맞는 종목이 없습니다.")

    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    main()
