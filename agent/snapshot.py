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
        active_ob = ob[ob['MitigatedIndex'].isna()].tail(2) if ob is not None else []
        active_fvg = fvg[fvg['MitigatedIndex'].isna()].tail(2) if fvg is not None else []
        
        return {
            "bos_choch": last_bos,
            "active_ob": active_ob.to_dict('records') if isinstance(active_ob, pd.DataFrame) else [],
            "active_fvg": active_fvg.to_dict('records') if isinstance(active_fvg, pd.DataFrame) else []
        }
    except Exception:
        return {}

def generate_snapshot(symbol: str):
    ticker = "GC=F" if symbol.upper() == "XAUUSD" else "NQ=F"
    
    # Tarik H1, M15, M5, M1
    df_h1 = yf.download(ticker, period="1mo", interval="1h", progress=False)
    df_m15 = yf.download(ticker, period="5d", interval="15m", progress=False)
    df_m5 = yf.download(ticker, period="5d", interval="5m", progress=False)
    df_m1 = yf.download(ticker, period="5d", interval="1m", progress=False)

    def clean_df(df):
        if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)
        return df.reset_index().rename(columns={"Datetime": "timestamps", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})

    df_h1, df_m15, df_m5, df_m1 = clean_df(df_h1), clean_df(df_m15), clean_df(df_m5), clean_df(df_m1)

    if df_h1.empty or df_m15.empty or df_m5.empty or df_m1.empty: 
        raise ValueError("Data kosong.")

    current_price = round(float(df_m1['close'].iloc[-1]), 2)
    
    df_h1['ema20'] = df_h1['close'].ewm(span=20).mean()
    df_h1['ema50'] = df_h1['close'].ewm(span=50).mean()
    trend_h1 = "BULLISH" if df_h1['ema20'].iloc[-1] > df_h1['ema50'].iloc[-1] else "BEARISH"
    
    smc_h1 = get_smc_data(df_h1.tail(100), "H1")
    smc_m15 = get_smc_data(df_m15.tail(100), "M15")
    smc_m5 = get_smc_data(df_m5.tail(100), "M5")
    smc_m1 = get_smc_data(df_m1.tail(100), "M1")
    sessions = get_session_lines(df_h1)

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
