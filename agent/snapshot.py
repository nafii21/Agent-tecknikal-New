import pandas as pd
import yfinance as yf
import pytz
from datetime import datetime
from smartmoneyconcepts import smc
import logging

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

def to_utc(ts_series):
    """Fungsi aman buat ngubah waktu ke UTC"""
    s = pd.to_datetime(ts_series)
    if s.dt.tz is None:
        return s.dt.tz_localize('UTC')
    return s.dt.tz_convert('UTC')

# Fungsi buat nentuin Sesi
def get_session_lines(df):
    """Ngitung High/Low Sesi Asia, London, NY untuk hari ini"""
    df = df.copy()
    df['ts_utc'] = to_utc(df['timestamps'])
    
    # Filter hari ini
    today = datetime.now(pytz.utc).date()
    today_df = df[df['ts_utc'].dt.date == today]
    
    sessions = {}
    for name, start, end in [
        ("Asia", 0, 8),      # 00:00 - 08:00 UTC
        ("London", 7, 16),   # 07:00 - 16:00 UTC
        ("New York", 12, 21) # 12:00 - 21:00 UTC
    ]:
        mask = (today_df['ts_utc'].dt.hour >= start) & (today_df['ts_utc'].dt.hour < end)
        sdf = today_df[mask]
        if not sdf.empty:
            sessions[name] = {
                "high": round(float(sdf['high'].max()), 2),
                "low": round(float(sdf['low'].min()), 2)
            }
    return sessions

def get_smc_data(df, timeframe_name):
    """Deteksi SMC pakai library smartmoneyconcepts"""
    if len(df) < 20: return {}
    
    # Siapkan data buat library SMC
    smc_df = df.set_index('timestamps')[['open', 'high', 'low', 'close', 'volume']].copy()
    smc_df.index = pd.to_datetime(smc_df.index).tz_localize(None) # Paksa jadi tz-naive biar SMC ga error
    
    try:
        swing_hl = smc.swing_highs_lows(smc_df, swing_length=10)
        bos_choch = smc.bos_choch(smc_df, swing_hl)
        ob = smc.ob(smc_df, swing_hl)
        fvg = smc.fvg(smc_df)
        
        # Ambil data terakhir yang relevan
        last_bos = bos_choch.dropna(subset=['BOS', 'CHOCH']).tail(1).to_dict('records')
        active_ob = ob[ob['MitigatedIndex'].isna()].tail(3) if ob is not None else []
        active_fvg = fvg[fvg['MitigatedIndex'].isna()].tail(3) if fvg is not None else []
        
        return {
            "bos_choch": last_bos,
            "active_ob": active_ob.to_dict('records') if isinstance(active_ob, pd.DataFrame) else [],
            "active_fvg": active_fvg.to_dict('records') if isinstance(active_fvg, pd.DataFrame) else []
        }
    except Exception as e:
        print(f"SMC Error {timeframe_name}: {e}")
        return {}

def generate_snapshot(symbol: str) -> str:
    # 1. Tarik Data H1 (HTF Context)
    ticker = "GC=F" if symbol.upper() == "XAUUSD" else "NQ=F"
    df_h1 = yf.download(ticker, period="1mo", interval="1h", progress=False)
    if hasattr(df_h1.columns, 'levels'): df_h1.columns = df_h1.columns.get_level_values(0)
    df_h1 = df_h1.reset_index().rename(columns={"Datetime": "timestamps", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    
    # 2. Tarik Data M5 (LTF Confirmation)
    df_m5 = yf.download(ticker, period="5d", interval="5m", progress=False)
    if hasattr(df_m5.columns, 'levels'): df_m5.columns = df_m5.columns.get_level_values(0)
    df_m5 = df_m5.reset_index().rename(columns={"Datetime": "timestamps", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})

    if df_h1.empty or df_m5.empty:
        raise ValueError("Data market gagal diambil (H1/M5 kosong).")

    current_price = round(float(df_m5['close'].iloc[-1]), 2)

    # 3. Hitung SMC H1 & M5
    smc_h1 = get_smc_data(df_h1.tail(100), "H1")
    smc_m5 = get_smc_data(df_m5.tail(100), "M5")
    
    # 4. Hitung Session Lines H1
    sessions = get_session_lines(df_h1)

    # 5. Susun Laporan
    report = f"===== CURRENT PRICE =====\n{symbol}: {current_price}\n\n"
    
    report += "===== SESSION LINES (H1) =====\n"
    for s_name, s_data in sessions.items():
        report += f"{s_name}: High={s_data['high']}, Low={s_data['low']}\n"
    
    report += "\n===== SMC H1 (HTF CONTEXT) =====\n"
    report += f"Last BOS/CHoCH: {smc_h1.get('bos_choch', [])}\n"
    report += f"Active OB: {smc_h1.get('active_ob', [])}\n"
    report += f"Active FVG: {smc_h1.get('active_fvg', [])}\n"

    report += "\n===== SMC M5 (LTF CONFIRMATION) =====\n"
    report += f"Last BOS/CHoCH: {smc_m5.get('bos_choch', [])}\n"
    report += f"Active OB: {smc_m5.get('active_ob', [])}\n"
    report += f"Active FVG: {smc_m5.get('active_fvg', [])}\n"

    # 6. Ambil Data Fundamental (Makro)
    try:
        df_dxy = yf.Ticker("DX-Y.NYB").history(period="5d", interval="1d")
        df_yield = yf.Ticker("^TNX").history(period="5d", interval="1d")
        dxy_change = ((df_dxy['Close'].iloc[-1] - df_dxy['Close'].iloc[-2]) / df_dxy['Close'].iloc[-2]) * 100
        yield_change = ((df_yield['Close'].iloc[-1] - df_yield['Close'].iloc[-2]) / df_yield['Close'].iloc[-2]) * 100
        
        report += f"\n===== MAKRO =====\n"
        report += f"DXY: {dxy_change:+.2f}% | US10Y: {yield_change:+.2f}%\n"
    except:
        pass

    return report
