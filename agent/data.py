import os, httpx, time
import pandas as pd
import yfinance as yf
import logging

# Matiin warning
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

FCS_KEY = os.getenv("FCS_API_KEY")

# Simbol yang didukung FCS API
FCS_SYMBOLS = {
    "XAUUSD": "XAUUSD",
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY"
}

# Simbol yang pakai yfinance (karena FCS gak punya)
YF_SYMBOLS = {
    "NASDAQ": "NQ=F",
    "BTCUSD": "BTC-USD"
}

TF_MAP_FCS = {
    "D1": "1D",
    "H4": "4h",
    "H1": "1h",
    "M15": "15m"
}

TF_MAP_YF = {
    "D1": {"interval": "1d", "period": "1y"},
    "H4": {"interval": "1h", "period": "1mo"},
    "H1": {"interval": "1h", "period": "5d"},
    "M15": {"interval": "15m", "period": "5d"}
}

MACRO_FCS = {
    "DXY": "DXY",      
    "OIL": "WTI",      
    "US10Y": "US10Y"   
}

# --- FUNGSI FCS API ---
def fetch_fcs_history(symbol: str, interval: str) -> pd.DataFrame:
    try:
        url = f"https://api-v4.fcsapi.com/forex/history?symbol={symbol}&period={interval}&access_key={FCS_KEY}"
        resp = httpx.get(url, timeout=20).json()
        
        if not resp.get("status") or "response" not in resp:
            raise ValueError(f"FCS Error [{symbol} {interval}]: {resp.get('msg', 'No data')}")
            
        raw_data = resp["response"]
        records = []
        for ts, vals in raw_data.items():
            records.append({
                "timestamps": pd.to_datetime(int(ts), unit='s'),
                "open": float(vals.get("o", 0)),
                "high": float(vals.get("h", 0)),
                "low": float(vals.get("l", 0)),
                "close": float(vals.get("c", 0)),
                "volume": float(vals.get("v", 1)) if "v" in vals else 1.0
            })
            
        df = pd.DataFrame(records)
        if df.empty: raise ValueError(f"FCS Error [{symbol} {interval}]: Data kosong")
        return df.sort_values("timestamps").reset_index(drop=True)
    except Exception as e:
        raise e

# --- FUNGSI YFINANCE ---
def fetch_yfinance_history(ticker: str, timeframe: str) -> pd.DataFrame:
    try:
        tk = yf.Ticker(ticker)
        params = TF_MAP_YF[timeframe]
        df = tk.history(interval=params["interval"], period=params["period"], timeout=10)
        
        if df.empty: raise ValueError(f"yfinance Error: Data kosong")
        
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        if "volume" not in df.columns: df["volume"] = 1
        df = df.reset_index().rename(columns={"Datetime": "timestamps", "Date": "timestamps"})
        
        if timeframe == "H4":
            df = df.set_index('timestamps')
            df = df.resample('4h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
            
        return df
    except Exception as e:
        raise e

# --- FUNGSI UTAMA ---
def fetch_all_data(symbol: str) -> dict:
    if not FCS_KEY:
        raise ValueError("API Key FCS API kosong di GitHub Secrets!")

    data_dict = {}
    symbol_upper = symbol.upper()
    
    # 1. TARIK DATA UTAMA
    if symbol_upper in FCS_SYMBOLS:
        print(f"Fetching {symbol} from FCS API (Delay 22s)...")
        fcs_sym = FCS_SYMBOLS[symbol_upper]
        for tf_name, interval in TF_MAP_FCS.items():
            try:
                df = fetch_fcs_history(fcs_sym, interval)
                if df is not None: data_dict[tf_name] = df
            except Exception as e:
                raise ValueError(f"Gagal narik data {tf_name} ({symbol}): {str(e)}")
            finally:
                time.sleep(22) # Jeda FCS
                
    elif symbol_upper in YF_SYMBOLS:
        print(f"Fetching {symbol} from yfinance...")
        yf_sym = YF_SYMBOLS[symbol_upper]
        for tf_name in TF_MAP_YF.keys():
            try:
                df = fetch_yfinance_history(yf_sym, tf_name)
                if df is not None: data_dict[tf_name] = df
            except Exception as e:
                raise ValueError(f"Gagal narik data {tf_name} ({symbol}): {str(e)}")
    else:
        raise ValueError(f"Simbol {symbol} tidak didukung di sistem ini.")

    if "D1" not in data_dict or "H4" not in data_dict:
        raise ValueError("Data Utama (D1/H4) gagal ditarik.")

    # 2. TARIK DATA MAKRO (Selalu pakai FCS API)
    macro_data = {}
    if symbol_upper in FCS_SYMBOLS: # Cuma narik makro kalau pake FCS biar ga makan waktu lama
        for macro_key, macro_sym in MACRO_FCS.items():
            try:
                df_m = fetch_fcs_history(macro_sym, "1D")
                if df_m is not None and len(df_m) >= 2:
                    change = ((df_m['close'].iloc[-1] - df_m['close'].iloc[-2]) / df_m['close'].iloc[-2]) * 100
                    macro_data[macro_key] = {"price": round(float(df_m['close'].iloc[-1]), 2), "change_pct": round(float(change), 2)}
            except Exception as e:
                print(f"Macro {macro_key} gagal: {e}")
            finally:
                time.sleep(22)

    print("Data fetching selesai!")
    return {"main": data_dict, "macro": macro_data}
