import yfinance as yf
import pandas as pd

SYMBOLS = {
    "XAUUSD": "GC=F", 
    "NASDAQ": "NQ=F",
    "EURUSD": "EURUSD=X", 
    "GBPUSD": "GBPUSD=X", 
    "USDJPY": "JPY=X",
    "BTCUSD": "BTC-USD"
}

MACRO_TICKERS = {"DXY": "DX-Y.NYB", "OIL": "CL=F", "US10Y": "^TNX"}

TF_MAP = {
    "MN1": {"interval": "1mo", "period": "10y"},
    "W1": {"interval": "1wk", "period": "5y"},
    "D1": {"interval": "1d", "period": "1y"},
    "H4": {"interval": "1h", "period": "1mo"},
    "H1": {"interval": "1h", "period": "5d"},
    "M15": {"interval": "15m", "period": "5d"}
}

def fetch_all_data(symbol: str) -> dict:
    ticker = SYMBOLS.get(symbol.upper(), symbol)
    data_dict = {}
    
    # Ambil data Multi-Timeframe Utama (Tambahin timeout biar ga hang)
    for tf_name, params in TF_MAP.items():
        try:
            df = yf.download(ticker, interval=params["interval"], period=params["period"], progress=False, timeout=10)
            if not df.empty:
                if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)
                data_dict[tf_name] = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        except Exception as e:
            pass
            
    # Ambil data Makro (Fundamental Proxy)
    macro_data = {}
    for name, tick in MACRO_TICKERS.items():
        try:
            df_m = yf.download(tick, period="5d", interval="1d", progress=False, timeout=10)
            if not df_m.empty:
                if hasattr(df_m.columns, 'levels'): df_m.columns = df_m.columns.get_level_values(0)
                change = ((df_m['Close'].iloc[-1] - df_m['Close'].iloc[-2]) / df_m['Close'].iloc[-2]) * 100
                macro_data[name] = {"price": round(float(df_m['Close'].iloc[-1]), 2), "change_pct": round(float(change), 2)}
        except:
            pass
            
    return {"main": data_dict, "macro": macro_data}
