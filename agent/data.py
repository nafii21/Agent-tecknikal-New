import os, httpx, yfinance as yf
import pandas as pd
import logging

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

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
    "H4": "1h",  
    "H1": "1h",
    "M15": "15min"
}

def fetch_twelvedata_xauusd():
    if not TWELVE_KEY:
        raise ValueError("❌ TWELVE_DATA_API_KEY kosong di GitHub Secrets!")

    data_dict = {}
    for tf_name, interval in TWELVE_TF_MAP.items():
        try:
            url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={interval}&outputsize=200&apikey={TWELVE_KEY}"
            resp = httpx.get(url, timeout=15).json()
            
            if "values" not in resp:
                # Nangkep pesan error asli dari Twelve Data
                error_msg = resp.get('message', 'Unknown Error')
                raise ValueError(f"TwelveData Error [{tf_name}]: {error_msg}")
                
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
            
            if tf_name == "H4":
                df = df.set_index('timestamps')
                df = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()

            data_dict[tf_name] = df
        except Exception as e:
            # Kalau gagal di satu TF, kita lempar errornya biar berhenti
            raise ValueError(f"TwelveData Request Error [{tf_name}]: {str(e)}")
            
    return data_dict

def fetch_yfinance_data(symbol):
    ticker = SYMBOLS.get(symbol.upper(), symbol)
    data_dict = {}
    
    try:
        tk = yf.Ticker(ticker)
    except Exception as e:
        raise ValueError(f"Yfinance Ticker Error: {e}")

    for tf_name, params in TF_MAP.items():
        try:
            df = tk.history(interval=params["interval"], period=params["period"], timeout=10)
            if not df.empty:
                df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
                if "volume" not in df.columns: df["volume"] = 1
                df = df.reset_index().rename(columns={"Datetime": "timestamps", "Date": "timestamps"})
                
                if tf_name == "H4":
                    df = df.set_index('timestamps')
                    df = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
                
                data_dict[tf_name] = df
            else:
                raise ValueError(f"yfinance data kosong untuk {tf_name}")
        except Exception as e:
            raise ValueError(f"Yfinance Error [{tf_name}]: {str(e)}")
    return data_dict

def fetch_all_data(symbol: str) -> dict:
    data_dict = {}
    
    if symbol.upper() == "XAUUSD":
        print("Fetching XAUUSD from TwelveData...")
        try:
            data_dict = fetch_twelvedata_xauusd()
        except Exception as td_error:
            print(f"⚠️ TwelveData Gagal: {td_error}")
            print("Mencoba beralih ke yfinance...")
            try:
                data_dict = fetch_yfinance_data(symbol)
            except Exception as yf_error:
                # Kalau dua-duanya gagal, kita lempar error gabungan ke Telegram
                raise RuntimeError(f"Data Gagal Diambil.\n\nTwelveData: {td_error}\nYFinance: {yf_error}")
    else:
        try:
            data_dict = fetch_yfinance_data(symbol)
        except Exception as yf_error:
            raise RuntimeError(f"Yfinance Gagal: {yf_error}")
    
    # --- DATA MAKRO ---
    macro_data = {}
    for name, tick in MACRO_TICKERS.items():
        try:
            tk = yf.Ticker(tick)
            df_m = tk.history(period="5d", interval="1d", timeout=10)
            if not df_m.empty:
                df_m = df_m.reset_index()
                change = ((df_m['Close'].iloc[-1] - df_m['Close'].iloc[-2]) / df_m['Close'].iloc[-2]) * 100
                macro_data[name] = {"price": round(float(df_m['Close'].iloc[-1]), 2), "change_pct": round(float(change), 2)}
        except:
            pass
            
    return {"main": data_dict, "macro": macro_data}
