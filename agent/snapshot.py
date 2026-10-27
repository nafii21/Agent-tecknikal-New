import pandas as pd
import pandas_ta_classic as ta
from datetime import datetime
import pytz
from agent.news import get_market_news

def get_market_session():
    now_utc = datetime.now(pytz.utc)
    hour = now_utc.hour
    if 0 <= hour < 7: return "ASIA (Tokyo)"
    elif 7 <= hour < 12: return "LONDON"
    elif 12 <= hour < 16: return "OVERLAP (London & New York) - HIGH VOLATILITY"
    elif 16 <= hour < 21: return "NEW YORK"
    else: return "AFTER HOURS (Low Liquidity)"

# --- FUNGSI SATPAM FORMAT (Biar nggak error kalau data kosong) ---
def safe_fmt(val, fmt):
    try:
        if val is None or pd.isna(val):
            return "N/A"
        return f"{float(val):{fmt}}"
    except:
        return "N/A"

def generate_snapshot(symbol: str, raw_data: dict) -> str:
    main_data = raw_data["main"]
    macro = raw_data["macro"]
    
    if "D1" not in main_data or "H4" not in main_data: return "Data gagal diambil."
    
    now_wib = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%A, %Y-%m-%d %H:%M WIB")
    session = get_market_session()
    
    report = f"===== WAKTU & SESI =====\n"
    report += f"Waktu Server (WIB): {now_wib}\n"
    report += f"Sesi Aktif: {session}\n\n"
    
    # 1. Loop Multi-Timeframe
    for tf in ["D1", "H4", "H1", "M15"]:
        if tf not in main_data: continue
        df = main_data[tf].copy()
        
        # Indikator Utama
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        last = df.iloc[-1]
        trend = "UP" if last['close'] > last['ema20'] else "DOWN"
        
        # Cari Swing High / Low Terakhir (Window 10 candle)
        df['swing_high'] = df['high'].rolling(window=10, center=True).max()
        df['swing_low'] = df['low'].rolling(window=10, center=True).min()
        
        # Ambil swing terakhir yang valid
        last_swing_high = df['swing_high'].dropna().iloc[-1] if not df['swing_high'].dropna().empty else last['high']
        last_swing_low = df['swing_low'].dropna().iloc[-1] if not df['swing_low'].dropna().empty else last['low']
        
        report += f"===== {symbol} {tf} =====\n"
        report += f"Close: {safe_fmt(last['close'], '.2f')} | EMA20: {safe_fmt(last['ema20'], '.2f')} | EMA50: {safe_fmt(last['ema50'], '.2f')}\n"
        report += f"RSI: {safe_fmt(last['rsi'], '.1f')} | ATR: {safe_fmt(last['atr'], '.2f')} | Trend: {trend}\n"
        report += f"Swing High: {safe_fmt(last_swing_high, '.2f')} | Swing Low: {safe_fmt(last_swing_low, '.2f')}\n"
        
        # Hitung Pivot & Fibo Lengkap (D1, H4)
        if tf in ["D1", "H4"]:
            prev = df.iloc[-2]
            high, low, close = prev['high'], prev['low'], prev['close']
            p = (high + low + close) / 3
            r1, s1 = (2*p) - low, (2*p) - high
            
            diff = high - low
            fibo_382 = high - (diff * 0.382)
            fibo_50 = high - (diff * 0.5)
            fibo_618 = high - (diff * 0.618)
            fibo_786 = high - (diff * 0.786)
            
            report += f"\n[ LEVEL FIBO & PIVOT {tf} ]\n"
            report += f"Pivot: {safe_fmt(p, '.2f')} | R1: {safe_fmt(r1, '.2f')} | S1: {safe_fmt(s1, '.2f')}\n"
            report += f"Fibo 38.2%: {safe_fmt(fibo_382, '.2f')} | Fibo 50%: {safe_fmt(fibo_50, '.2f')} | Fibo 61.8%: {safe_fmt(fibo_618, '.2f')} | Fibo 78.6%: {safe_fmt(fibo_786, '.2f')}\n\n"

    # 2. Konteks Makro
    report += "===== KONTEKS MAKRO (FUNDAMENTAL) =====\n"
    if "DXY" in macro: report += f"DXY (Dollar): {macro['DXY']['price']} ({safe_fmt(macro['DXY']['change_pct'], '+.2f')}%)\n"
    if "US10Y" in macro: report += f"US10Y (Bond Yield): {macro['US10Y']['price']}% ({safe_fmt(macro['US10Y']['change_pct'], '+.2f')}%)\n"
    report += "\n"
    
    # 3. Berita
    news_text = get_market_news(symbol)
    report += news_text
    
    return report
