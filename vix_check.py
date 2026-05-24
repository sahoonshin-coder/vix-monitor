import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import requests
import os

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

def get_vix_term_structure_data():
    end_date = datetime.today()
    start_date = end_date - timedelta(days=90)

    tickers = {
        'VIX': '^VIX',
        'V1_Short': 'VIXY',
        'V2_Mid': 'VXZ'
    }

    df_list = []
    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date)['Close']
            if data.empty:
                print(f"[경고] {ticker} 데이터 없음")
                continue
            data = pd.Series(data.values.flatten(), index=data.index, name=name)
            df_list.append(data)
        except Exception as e:
            print(f"[오류] {ticker}: {e}")

    if not df_list:
        raise RuntimeError("모든 티커 데이터 수집 실패")

    return pd.concat(df_list, axis=1).dropna()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': text})

def send_telegram_photo(photo_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(photo_path, 'rb') as f:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID}, files={'photo': f})

def analyze_and_plot():
    df = get_vix_term_structure_data()

    latest = df.iloc[-1]
    latest_date = df.index[-1].strftime('%Y-%m-%d')

    vix_val = latest['VIX']
    v1_val = latest['V1_Short']
    v2_val = latest['V2_Mid']

    if vix_val < v1_val:
        status = "★ [안정] 콘탱고(Contango) 상태"
        description = "시장 참여자들이 미래를 더 불안하게 보는 정상적인 상태입니다."
    else:
        status = "⚠ [위험] 백워데이션(Backwardation) 전조"
        description = "단기 공포(VIX)가 미래 보험료를 넘어섰습니다. 주식 매도/자산 대피를 검토하세요."

    message = f"""[{latest_date}] VIX 모니터링
- VIX 현물: {vix_val:.2f}
- 근월물(V1): {v1_val:.2f}
- 차월물(V2): {v2_val:.2f}
{status}
{description}"""

    # 차트 생성
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['VIX'], label='VIX', color='#2ca02c', linewidth=2)
    plt.plot(df.index, df['V1_Short'], label='V1 (VIXY)', color='#1f77b4', linestyle='--')
    plt.plot(df.index, df['V2_Mid'], label='V2 (VXZ)', color='#ff7f0e', linestyle='-.')

    danger_zone = df['VIX'] > df['V1_Short']
    for i in range(len(df) - 1):
        if danger_zone.iloc[i]:
            plt.axvspan(df.index[i], df.index[i + 1], color='red', alpha=0.15)

    plt.title(f'VIX Term Structure ({latest_date})', fontsize=14, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Index / Price ($)')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='upper left')
    plt.tight_layout()

    chart_path = 'vix_chart.png'
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')

    send_telegram_message(message)
    send_telegram_photo(chart_path)
    print("텔레그램 발송 완료")

analyze_and_plot()
