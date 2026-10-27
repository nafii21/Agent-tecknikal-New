import os, httpx, time
import pandas as pd
import yfinance as yf
import logging

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

TWELVE_KEY = os.getenv("TWELVE_DATA_API_KEY")

# Pair yang pakai Twelve Data (Cepat & Kuota Harian 800)
TWELVE_SYMBOLS = {
    "XAUUSD": "XAU/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY"
}

# Pair yang pakai yfinance (Karena Twelve Data Free gak support)
YF_SYMBOLS = {
    "NASDAQ": "NQ=F",
    "BTCUSD": "BTC-USD"
}

TF_MAP_TWELVE = {"D1": "1day", "H4": "1h", "H1": "1h", "M15": "15min"}
TF_MAP_YF = {
    "D1": {"interval": "1d", "period": "1y"},
    "H4": {"interval": "1h", "period": "1mo"},
    "H1": {"interval": "1h", "period": "5d"},
    "M15": {"interval": "15m", "period": "5d"}
}

MACRO_TICKERS = {"DXY": "DX-Y.NYB", "OIL": "CL=F", "US10Y": "^TNX"}

def fetch_twelvedata_history(symbol: str, interval: str) -> pd.DataFrame:
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=200&apikey={TWELVE_KEY}"
        resp = httpx.get(url, timeout=15).json()
        
        if "values" not in resp:
            raise ValueError(f"TwelveData Error: {resp.get('message', 'No data')}")
            
        df = pd.DataFrame(resp["values"]).rename(columns={"datetime": "timestamps"})
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df = df.dropna(subset=["open", "high", "low", "close"])
        df["volume"] = 1
        
        df["timestamps"] = pd.to_datetime(df["timestamps"])
        df = df.sort_values("timestamps").reset_index(drop=True)
        
        if interval == "1h" and len(df) > 50:
            # Khusus H4, kita harus resample karena Twelve Data free gak ada 4h
            # Tapi ini opsional, kita biarin pakai 1h biar simpel
            pass
            
        return df
    except Exception as e:
        raise e

def fetch_yfinance_history(ticker: str, timeframe: str) -> pd.DataFrame:
    try:
        tk = yf.Ticker(ticker)
        params = TF_MAP_YF[timeframe]
        df = tk.history(interval=params["interval"], period=params["period"], timeout=10)
        
        if df.empty: raise ValueError("yfinance Error: Data kosong")
        
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        if "volume" not in df.columns: df["volume"] = 1
        df = df.reset_index().rename(columns={"Datetime": "timestamps", "Date": "timestamps"})
        
        if timeframe == "H4":
            df = df.set_index('timestamps')
            df = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
            
        return df
    except Exception as e:
        raise e

def fetch_all_data(symbol: str) -> dict:
    if not TWELVE_KEY:
        raise ValueError("TWELVE_DATA_API_KEY kosong di GitHub Secrets!")

    data_dict = {}
    symbol_upper = symbol.upper()
    
    # 1. DATA UTAMA
    if symbol_upper in TWELVE_SYMBOLS:
        print(f"Fetching {symbol} from TwelveData...")
        tw_sym = TWELVE_SYMBOLS[symbol_upper]
        for tf_name, interval in TF_MAP_TWELVE.items():
            try:
                df = fetch_twelvedata_history(tw_sym, interval)
                if tf_name == "H4":
                    df = df.set_index('timestamps')
                    df = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
                data_dict[tf_name] = df
            except Exception as e:
                raise ValueError(f"Gagal narik {tf_name} ({symbol}): {str(e)}")
            time.sleep(1) # Jeda tipis aja, Twelve Data limitnya longgar
            
    elif symbol_upper in YF_SYMBOLS:
        print(f"Fetching {symbol} from yfinance...")
        yf_sym = YF_SYMBOLS[symbol_upper]
        for tf_name in TF_MAP_YF.keys():
            try:
                df = fetch_yfinance_history(yf_sym, tf_name)
                data_dict[tf_name] = df
            except Exception as e:
                raise ValueError(f"Gagal narik {tf_name} ({symbol}): {str(e)}")
    else:
        raise ValueError(f"Simbol {symbol} tidak didukung.")

    # 2. DATA MAKRO
    macro_data = {}
    if symbol_upper in TWELVE_SYMBOLS:
        for macro_key, tick in MACRO_TICKERS.items():
            try:
                tk = yf.Ticker(tick)
                df_m = tk.history(period="5d", interval="1d", timeout=10)
                if not df_m.empty:
                    df_m = df_m.reset_index()
                    change = ((df_m['Close'].iloc[-1] - df_m['Close'].iloc[-2]) / df_m['Close'].iloc[-2]) * 100
                    macro_data[macro_key] = {"price": round(float(df_m['Close'].iloc[-1]), 2), "change_pct": round(float(change), 2)}
            except:
                pass

    print("Data fetching selesai!")
    return {"main": data_dict, "macro": macro_data}
