import pandas as pd
import yfinance as yf
import pytz
from datetime import datetime
from smartmoneyconcepts import smc
import logging

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

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
        active_ob = ob[ob['MitigatedIndex'].isna()].tail(3) if ob is not None else []
        active_fvg = fvg[fvg['MitigatedIndex'].isna()].tail(3) if fvg is not None else []
        
        return {
            "bos_choch": last_bos,
            "active_ob": active_ob.to_dict('records') if isinstance(active_ob, pd.DataFrame) else [],
            "active_fvg": active_fvg.to_dict('records') if isinstance(active_fvg, pd.DataFrame) else []
        }
    except Exception:
        return {}

def generate_snapshot(symbol: str):
    ticker = "GC=F" if symbol.upper() == "XAUUSD" else "NQ=F"
    
    df_h1 = yf.download(ticker, period="1mo", interval="1h", progress=False)
    if hasattr(df_h1.columns, 'levels'): df_h1.columns = df_h1.columns.get_level_values(0)
    df_h1 = df_h1.reset_index().rename(columns={"Datetime": "timestamps", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    
    df_m5 = yf.download(ticker, period="5d", interval="5m", progress=False)
    if hasattr(df_m5.columns, 'levels'): df_m5.columns = df_m5.columns.get_level_values(0)
    df_m5 = df_m5.reset_index().rename(columns={"Datetime": "timestamps", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})

    if df_h1.empty or df_m5.empty: raise ValueError("Data kosong.")

    current_price = round(float(df_m5['close'].iloc[-1]), 2)
    
    # HITUNG STRUKTUR MENTAH H1 UNTUK CADANGAN AI
    df_h1['ema20'] = df_h1['close'].ewm(span=20).mean()
    df_h1['ema50'] = df_h1['close'].ewm(span=50).mean()
    trend_h1 = "BULLISH" if df_h1['ema20'].iloc[-1] > df_h1['ema50'].iloc[-1] else "BEARISH"
    
    recent_swing_high = round(float(df_h1['high'].tail(50).max()), 2)
    recent_swing_low = round(float(df_h1['low'].tail(50).min()), 2)
    last_3_highs = [round(float(x), 2) for x in df_h1['high'].tail(50).nlargest(3).tolist()]
    last_3_lows = [round(float(x), 2) for x in df_h1['low'].tail(50).nsmallest(3).tolist()]

    smc_h1 = get_smc_data(df_h1.tail(100), "H1")
    smc_m5 = get_smc_data(df_m5.tail(100), "M5")
    sessions = get_session_lines(df_h1)

    report = f"===== CURRENT PRICE =====\n{symbol}: {current_price}\n\n"
    
    report += "===== STRUKTUR MENTAH H1 (FALLBACK KONTEKS) =====\n"
    report += f"Trend EMA: {trend_h1}\n"
    report += f"Swing High Terdekat: {recent_swing_high}\n"
    report += f"Swing Low Terdekat: {recent_swing_low}\n"
    report += f"3 High Terakhir: {last_3_highs}\n"
    report += f"3 Low Terakhir: {last_3_lows}\n\n"

    report += "===== SESSION LINES (H1) =====\n"
    for s_name, s_data in sessions.items():
        report += f"{s_name}: High={s_data['high']}, Low={s_data['low']}\n"
    
    report += "\n===== SMC H1 =====\n"
    report += f"Last BOS/CHoCH: {smc_h1.get('bos_choch', [])}\n"
    report += f"Active OB: {smc_h1.get('active_ob', [])}\n"
    report += f"Active FVG: {smc_h1.get('active_fvg', [])}\n"

    report += "\n===== SMC M5 =====\n"
    report += f"Last BOS/CHoCH: {smc_m5.get('bos_choch', [])}\n"
    report += f"Active OB: {smc_m5.get('active_ob', [])}\n"
    report += f"Active FVG: {smc_m5.get('active_fvg', [])}\n"

    return report, df_h1, sessions
