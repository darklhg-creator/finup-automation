import FinanceDataReader as fdr
import requests
import os
from datetime import datetime

# 이격도 채널 웹훅
IGYEOK_WEBHOOK_URL = "https://discord.com/api/webhooks/1461902939139604684/ZdCdITanTb3sotd8LlCYlJzSYkVLduAsjC6CD2h26X56wXoQRw7NY72kTNzxTI6UE4Pi"

def check_market_open():
    """오늘 주식 시장이 열리는 날인지 확인"""
    now = datetime.now()
    
    # 1. 주말 체크 (5: 토요일, 6: 일요일)
    if now.weekday() >= 5:
        return False, "오늘은 즐거운 주말입니다. 주식 시장이 열리지 않습니다. ☕"

    # 2. 공휴일 체크 (주가 데이터를 불러와서 오늘 날짜가 있는지 확인)
    try:
        # 삼성전자(005930)의 가장 최근 영업일 데이터를 가져옴
        df = fdr.DataReader('005930', unit='d').tail(1)
        last_market_date = df.index[-1].date()
        today_date = now.date()

        # 만약 평일인데 가장 최근 데이터 날짜가 오늘이 아니라면 (공휴일일 가능성 높음)
        # 단, 아침 일찍 실행 시 오늘 데이터가 아직 안 올라왔을 수 있으므로 
        # 개장 시간(09:00) 이후에 더 정확하게 작동합니다.
        if today_date > last_market_date and now.hour >= 9:
            # 평일이지만 주가 데이터가 오늘 날짜가 아님 = 휴장일(공휴일)일 확률 높음
            return False, "오늘은 공휴일 또는 거래소 지정 휴장일입니다. 분석을 쉬어갑니다. 📅"
            
    except Exception as e:
        print(f"휴장일 체크 중 오류: {e}")
        # 오류 발생 시 안전하게 개장일로 가정하고 진행하거나, 기본값 처리
        return True, "개장 여부 확인 불가 (진행 시도)"

    return True, "개장일입니다."

def main():
    print("📊 시장 개장 여부 확인 중...")
    
    # 1. 휴장일 여부 확인
    is_open, msg = check_market_open()
    
    if not is_open:
        # 휴장일이면 이격도 채널에 알림만 보내고 종료
        print(f"📢 {msg}")
        requests.post(IGYEOK_WEBHOOK_URL, json={'content': f"🔔 **휴장 안내**\n> {msg}"})
        return

    # 2. 개장일일 경우에만 아래 분석 로직 실행
    print("🚀 장이 열렸습니다. 이격도 분석을 시작합니다.")
    
    # [이후 기존 targets.txt 읽기 및 이격도 분석 로직...]
    if os.path.exists("targets.txt"):
        # ... 분석 진행 ...
        pass
    else:
        print("targets.txt 파일이 없습니다.")

if __name__ == "__main__":
    main()
