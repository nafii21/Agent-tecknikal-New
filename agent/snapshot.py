import pandas as pd
import httpx
import pytz
import os
from datetime import datetime
from smartmoneyconcepts import smc
import logging

logging.basicConfig(level=logging.INFO)

EXNESS_API_KEY = os.getenv("EXNESS_API_KEY")
BASE_URL = "https://api.exness.com"

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

def fetch_exness_data(symbol, interval, limit):
    """🔥 FUNGSI BARU: Narik data Candlestick langsung dari Exness 🔥"""
    if not EXNESS_API_KEY:
        raise ValueError("EXNESS_API_KEY kosong di GitHub Secrets.")

    # ⚠️ SESUAIKAN ENDPOINT & PARAMETER DENGAN DOKUMENTASI API EXNESS LU ⚠️
    # Contoh di bawah ini adalah standar REST API broker (bisa beda path/params)
    url = f"{BASE_URL}/api/v1/market/candles" 
    
    headers = {
        "EXNESS-API-KEY": EXNESS_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Mapping interval (sesuaikan string interval dengan dokumentasi Exness, misal '1h', '15m')
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", []) # Asumsi response Exness ada di key "data"
        
        if not data:
            return pd.DataFrame()

        # Konversi JSON ke DataFrame
        df = pd.DataFrame(data)
        
        # ⚠️ SESUAIKAN NAMA KOLOM DENGAN RESPONSE EXNESS LU ⚠️
        # Exness biasanya ngasih timestamp (ms), open, high, low, close, volume
        df = df.rename(columns={
            "time": "timestamps", "timestamp": "timestamps", 
            "open": "open", "high": "high", "low": "low", 
            "close": "close", "volume": "volume"
        })
        
        # Pastiin timestamp jadi datetime
        if 'timestamps' in df.columns:
            # Kalau timestamp-nya angka (milidetik), ubah ke datetime
            if pd.api.types.is_numeric_dtype(df['timestamps']):
                df['timestamps'] = pd.to_datetime(df['timestamps'], unit='ms')
            else:
                df['timestamps'] = pd.to_datetime(df['timestamps'])
                
        return df

    except Exception as e:
        logging.error(f"Gagal narik data {symbol} {interval} dari Exness: {e}")
        # Fallback: kembalikan DataFrame kosong biar error-nya ketangkep di generate_snapshot
        return pd.DataFrame()


def generate_snapshot(symbol: str):
    # Format simbol Exness (misal XAUUSD)
    exness_symbol = symbol.upper()
    
    # 🔥 TARIK DATA LANGSUNG DARI EXNESS 🔥
    # Limit 100 candle terakhir, sesuaikan interval dengan API Exness
    df_h1 = fetch_exness_data(exness_symbol, interval="1h", limit=100)
    df_m15 = fetch_exness_data(exness_symbol, interval="15m", limit=100)
    df_m5 = fetch_exness_data(exness_symbol, interval="5m", limit=100)
    df_m1 = fetch_exness_data(exness_symbol, interval="1m", limit=100)

    # Pastiin data nggak kosong
    if df_h1.empty or df_m15.empty or df_m5.empty or df_m1.empty: 
        raise ValueError(f"Data kosong dari Exness untuk {symbol}. Cek dokumentasi API atau koneksi.")

    # Ambil harga terakhir dari M1
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
