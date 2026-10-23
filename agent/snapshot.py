import pandas as pd
import pandas_ta_classic as ta
from datetime import datetime
import pytz

def generate_snapshot(symbol: str, raw_data: dict) -> str:
    main_data = raw_data["main"]
    macro = raw_data["macro"]
    
    if "D1" not in main_data or "H4" not in main_data: return "Data gagal diambil."
    
    now_wib = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%A, %Y-%m-%d %H:%M WIB")
    
    report = f"===== WAKTU =====\nServer Time: {now_wib}\n\n"
    
    # 1. Loop Multi-Timeframe
    for tf in ["MN1", "W1", "D1", "H4", "H1", "M15"]:
        if tf not in main_data: continue
        df = main_data[tf].copy()
        
        # Hitung Indikator
        df['ema20'] = ta.ema(df['close'], length=20)
        df['ema50'] = ta.ema(df['close'], length=50)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        last = df.iloc[-1]
        trend = "UP" if last['close'] > last['ema20'] else "DOWN"
        
        report += f"===== {symbol} {tf} =====\n"
        report += f"Close: {last['close']:.2f} | EMA20: {last['ema20']:.2f} | EMA50: {last['ema50']:.2f}\n"
        report += f"RSI: {last['rsi']:.1f} | ATR: {last['atr']:.2f} | Trend: {trend}\n"
        
        # Kalkulasi Pivot & Fibo (Hanya buat D1)
        if tf == "D1":
            prev = df.iloc[-2]
            p = (prev['high'] + prev['low'] + prev['close']) / 3
            r1, s1 = (2*p) - prev['low'], (2*p) - prev['high']
            r2, s2 = p + (prev['high'] - prev['low']), p - (prev['high'] - prev['low'])
            fibo_50 = (prev['high'] + prev['low']) / 2
            
            report += f"\n[ LEVEL KUNCI D1 ]\nPivot: {p:.2f} | R1: {r1:.2f} | S1: {s1:.2f}\n"
            report += f"Fibo 50% (Sweet Spot): {fibo_50:.2f} | Prev High: {prev['high']:.2f} | Prev Low: {prev['low']:.2f}\n\n"
            
        # Ambil 5 candle terakhir
        recent = df.tail(5)[['open', 'high', 'low', 'close']].round(2).to_dict('records')
        report += f"Last 5 Candles: {recent}\n\n"

    # 2. Konteks Makro
    report += "===== KONTEKS MAKRO (FUNDAMENTAL) =====\n"
    if "DXY" in macro: report += f"DXY (Dollar): {macro['DXY']['price']} ({macro['DXY']['change_pct']:+.2f}%)\n"
    if "US10Y" in macro: report += f"US10Y (Bond Yield): {macro['US10Y']['price']}% ({macro['US10Y']['change_pct']:+.2f}%)\n"
    if "OIL" in macro: report += f"Oil (Brent): {macro['OIL']['price']} ({macro['OIL']['change_pct']:+.2f}%)\n"
    report += "Kesimpulan: Jika DXY & Yield naik, Gold cenderung tertekan turun.\n"
    
    return report
