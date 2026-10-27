import os, httpx, yfinance as yf
import pandas as pd

TWELVE_KEY = os.getenv("TWELVE_DATA_API_KEY")

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
    "D1": {"interval": "1d", "period": "1y"},
    "H4": {"interval": "1h", "period": "1mo"},
    "H1": {"interval": "1h", "period": "5d"},
    "M15": {"interval": "15m", "period": "5d"}
}

TWELVE_TF_MAP = {
    "D1": "1day",
    "H4": "4h",
    "H1": "1h",
    "M15": "15min"
}

def fetch_twelvedata_xauusd():
    """Fungsi khusus narik XAUUSD dari Twelve Data"""
    data_dict = {}
    for tf_name, interval in TWELVE_TF_MAP.items():
        try:
            url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={interval}&outputsize=100&apikey={TWELVE_KEY}"
            resp = httpx.get(url, timeout=15).json()
            
            if "values" not in resp:
                print(f"TwelveData Error {tf_name}: {resp.get('message', 'No data')}")
                continue
                
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
            
            data_dict[tf_name] = df
        except Exception as e:
            print(f"TwelveData Request Error {tf_name}: {e}")
            
    return data_dict

def fetch_all_data(symbol: str) -> dict:
    ticker = SYMBOLS.get(symbol.upper(), symbol)
    data_dict = {}
    
    # --- 1. ROUTING DATA UTAMA ---
    if symbol.upper() == "XAUUSD":
        print("Fetching XAUUSD from TwelveData...")
        data_dict = fetch_twelvedata_xauusd()
    else:
        # Pake yfinance buat pair lain (BTC, EUR, dll)
        for tf_name, params in TF_MAP.items():
            try:
                df = yf.download(ticker, interval=params["interval"], period=params["period"], progress=False, timeout=10, threads=False)
                if not df.empty:
                    if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)
                    data_dict[tf_name] = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
            except Exception as e:
                print(f"Gagal ambil {tf_name} (yfinance): {e}")
    
    # --- 2. DATA MAKRO (Selalu pake yfinance) ---
    macro_data = {}
    for name, tick in MACRO_TICKERS.items():
        try:
            df_m = yf.download(tick, period="5d", interval="1d", progress=False, timeout=10, threads=False)
            if not df_m.empty:
                if hasattr(df_m.columns, 'levels'): df_m.columns = df_m.columns.get_level_values(0)
                change = ((df_m['Close'].iloc[-1] - df_m['Close'].iloc[-2]) / df_m['Close'].iloc[-2]) * 100
                macro_data[name] = {"price": round(float(df_m['Close'].iloc[-1]), 2), "change_pct": round(float(change), 2)}
        except:
            pass
            
    return {"main": data_dict, "macro": macro_data}
