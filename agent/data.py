import os, httpx, time
import pandas as pd
import logging

logging.getLogger("yfinance").setLevel(logging.CRITICAL) # Biarin aja buat matiin warning

TWELVE_KEY = os.getenv("TWELVE_DATA_API_KEY")

# Semua pair dan makro sekarang pakai Twelve Data
TWELVE_SYMBOLS = {
    "XAUUSD": "XAU/USD",
    "BTCUSD": "BTC/USD",
    "NASDAQ": "QQQ",    # QQQ aman di free tier Twelve Data
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "DXY": "DXY",       # US Dollar Index
    "OIL": "WTI/USD",   # Minyak
    "US10Y": "US10Y"    # Yield
}

TF_MAP = {
    "D1": "1day",
    "H4": "1h",  
    "H1": "1h",
    "M15": "15min"
}

def fetch_twelvedata(symbol_name: str, interval: str, outputsize: int = 200):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol_name}&interval={interval}&outputsize={outputsize}&apikey={TWELVE_KEY}"
        resp = httpx.get(url, timeout=15).json()
        
        if "values" not in resp:
            return None
            
        df = pd.DataFrame(resp["values"]).rename(columns={"datetime": "timestamps"})
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df = df.dropna(subset=["open", "high", "low", "close"])
        
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(1).replace(0, 1)
        else:
            df["volume"] = 1
        
        df["timestamps"] = pd.to_datetime(df["timestamps"])
        df = df.sort_values("timestamps").reset_index(drop=True)
        
        return df
    except Exception as e:
        print(f"Error fetching {symbol_name} {interval}: {e}")
        return None

def fetch_all_data(symbol: str) -> dict:
    if not TWELVE_KEY:
        raise ValueError("API Key Twelve Data kosong di GitHub Secrets!")

    data_dict = {}
    tw_symbol = TWELVE_SYMBOLS.get(symbol.upper(), symbol)
    
    print(f"Fetching {symbol} from TwelveData...")
    
    # 1. Narik Data Utama (4 Timeframe)
    for tf_name, interval in TF_MAP.items():
        df = fetch_twelvedata(tw_symbol, interval)
        
        if df is not None:
            if tf_name == "H4":
                df = df.set_index('timestamps')
                df = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
            data_dict[tf_name] = df
        
        # Kasih jeda 1.5 detik biar nggak kena rate limit 8 req/menit Twelve Data
        time.sleep(1.5)
        
    if "D1" not in data_dict or "H4" not in data_dict:
        raise ValueError("Data Utama (D1/H4) gagal ditarik dari Twelve Data. Cek limit atau API Key.")

    # 2. Narik Data Makro
    macro_data = {}
    for macro_key, macro_sym in [("DXY", "DXY"), ("OIL", "WTI/USD"), ("US10Y", "US10Y")]:
        df_m = fetch_twelvedata(macro_sym, "1day", outputsize=5)
        if df_m is not None and len(df_m) >= 2:
            change = ((df_m['close'].iloc[-1] - df_m['close'].iloc[-2]) / df_m['close'].iloc[-2]) * 100
            macro_data[macro_key] = {"price": round(float(df_m['close'].iloc[-1]), 2), "change_pct": round(float(change), 2)}
        
        # Jeda lagi
        time.sleep(1.5)

    print("Data fetching selesai!")
    return {"main": data_dict, "macro": macro_data}
