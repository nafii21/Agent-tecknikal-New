import pandas as pd
import httpx
import pytz
import os
from datetime import datetime
from smartmoneyconcepts import smc
import logging

logging.basicConfig(level=logging.INFO)

TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
TWELVE_DATA_URL = "https://api.twelvedata.com/time_series"

def to_utc(ts_series):
    s = pd.to_datetime(ts_series)
    if s.dt.tz is None:
        return s.dt.tz_localize('UTC')
    return s.dt.tz_convert('UTC')

def get_session_lines(df):
    df = df.copy()
    df['ts_utc'] = to_utc(df['timestamps'])
    today = datetime.now(pytz.utc).date()
    today_df = df[df['ts_utc'].dt.date == today]
    sessions = {}
    for name, start, end in [("Asia", 0, 8), ("London", 7, 16), ("New York", 12, 21)]:
        mask = (today_df['ts_utc'].dt.hour >= start) & (today_df['ts_utc'].dt.hour < end)
        sdf = today_df[mask]
        if not sdf.empty:
            sessions[name] = {"high": round(float(sdf['high'].max()), 2), "low": round(float(sdf['low'].min()), 2)}
    return sessions

def get_smc_data(df, timeframe_name):
    if len(df) < 20: return {}
    smc_df = df.set_index('timestamps')[['open', 'high', 'low', 'close', 'volume']].copy()
    smc_df.index = pd.to_datetime(smc_df.index).tz_localize(None)
    try:
        swing_hl = smc.swing_highs_lows(smc_df, swing_length=10)
        bos_choch = smc.bos_choch(smc_df, swing_hl)
        ob = smc.ob(smc_df, swing_hl)
        fvg = smc.fvg(smc_df)
        
        last_bos = bos_choch.dropna(subset=['BOS', 'CHOCH']).tail(1).to_dict('records')
        active_ob = ob[ob['MitigatedIndex'].isna()].tail(2) if ob is not None else []
        active_fvg = fvg[fvg['MitigatedIndex'].isna()].tail(2) if fvg is not None else []
        
        return {
            "bos_choch": last_bos,
            "active_ob": active_ob.to_dict('records') if isinstance(active_ob, pd.DataFrame) else [],
            "active_fvg": active_fvg.to_dict('records') if isinstance(active_fvg, pd.DataFrame) else []
        }
    except Exception as e:
        logging.error(f"Error SMC {timeframe_name}: {e}")
        return {}

def fetch_twelvedata(symbol, interval, count=100):
    """🔥 FUNGSI BARU: Narik data dari Twelve Data 🔥"""
    if not TWELVE_DATA_API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY kosong di GitHub Secrets.")
    
    # 1. Mapping Simbol (Twelve Data butuh format spesifik)
    symbol_map = {
        "XAUUSD": "XAU/USD",
        "BTCUSD": "BTC/USD",
        "NASDAQ": "NDX", # Nasdaq 100
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY"
    }
    td_symbol = symbol_map.get(symbol.upper(), f"{symbol[:3]}/{symbol[3:]}") # Fallback (misal EURUSD -> EUR/USD)
    
    # 2. Mapping Interval (Twelve Data pakai 'min' bukan 'm')
    interval_map = {
        "1h": "1h",
        "15m": "15min",
        "5m": "5min",
        "1m": "1min"
    }
    td_interval = interval_map.get(interval, interval)
    
    params = {
        "symbol": td_symbol,
        "interval": td_interval,
        "outputsize": count,
        "apikey": TWELVE_DATA_API_KEY,
        "timezone": "UTC"
    }
    
    try:
        resp = httpx.get(TWELVE_DATA_URL, params=params, timeout=15)
        data = resp.json()
        
        # Cek kalau API ngebalikin error (misal limit habis atau simbol salah)
        if "status" in data and data["status"] == "error":
            logging.error(f"TwelveData Error ({td_symbol}): {data.get('message')}")
            return pd.DataFrame()
            
        values = data.get("values", [])
        if not values:
            return pd.DataFrame()
            
        df = pd.DataFrame(values)
        
        # Rename kolom dari Twelve Data ke format yang kita butuh
        df = df.rename(columns={"datetime": "timestamps"})
        
        # Twelve Data ngasih data dari terbaru ke terlama, kita harus urutin dari terlama ke terbaru
        df['timestamps'] = pd.to_datetime(df['timestamps'])
        df = df.sort_values(by='timestamps').reset_index(drop=True)
        
        # Pastiin tipe datanya float (karena Twelve Data ngasih string)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            else:
                df[col] = 0.0 # Kadang Forex nggak ada volume, kita isi 0
                
        return df[['timestamps', 'open', 'high', 'low', 'close', 'volume']]
        
    except Exception as e:
        logging.error(f"Gagal narik data {symbol} {interval} dari TwelveData: {e}")
        return pd.DataFrame()


def generate_snapshot(symbol: str):
    # 🔥 TARIK DATA DARI TWELVE DATA 🔥
    df_h1 = fetch_twelvedata(symbol, interval="1h", count=100)
    df_m15 = fetch_twelvedata(symbol, interval="15m", count=100)
    df_m5 = fetch_twelvedata(symbol, interval="5m", count=100)
    df_m1 = fetch_twelvedata(symbol, interval="1m", count=100)

    if df_h1.empty or df_m15.empty or df_m5.empty or df_m1.empty: 
        raise ValueError(f"Data kosong dari TwelveData untuk {symbol}. Cek limit API atau nama simbol.")

    current_price = round(float(df_m1['close'].iloc[-1]), 2)
    
    # Hitung EMA buat Trend H1
    df_h1['ema20'] = df_h1['close'].ewm(span=20).mean()
    df_h1['ema50'] = df_h1['close'].ewm(span=50).mean()
    trend_h1 = "BULLISH" if df_h1['ema20'].iloc[-1] > df_h1['ema50'].iloc[-1] else "BEARISH"
    
    # Hitung SMC
    smc_h1 = get_smc_data(df_h1.tail(100), "H1")
    smc_m15 = get_smc_data(df_m15.tail(100), "M15")
    smc_m5 = get_smc_data(df_m5.tail(100), "M5")
    smc_m1 = get_smc_data(df_m1.tail(100), "M1")
    sessions = get_session_lines(df_h1)

    # Bikin Report buat AI
    report = f"===== CURRENT PRICE =====\n{symbol}: {current_price}\n\n"
    report += "===== H1 CONTEXT =====\n"
    report += f"Trend: {trend_h1}\n"
    report += f"SMC H1: {smc_h1}\n\n"
    
    report += "===== M15 LIQUIDITY =====\n"
    report += f"SMC M15: {smc_m15}\n\n"

    report += "===== M5 TRIGGER DATA =====\n"
    report += f"SMC M5: {smc_m5}\n\n"

    report += "===== M1 TRIGGER DATA =====\n"
    report += f"SMC M1: {smc_m1}\n\n"

    report += "===== SESSION LINES =====\n"
    for s_name, s_data in sessions.items():
        report += f"{s_name}: High={s_data['high']}, Low={s_data['low']}\n"

    return report, df_h1, df_m15, df_m5, df_m1, sessions
