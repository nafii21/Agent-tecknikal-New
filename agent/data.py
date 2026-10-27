import os, httpx, time
import pandas as pd
import logging

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

FCS_KEY = os.getenv("FCS_API_KEY")

FCS_SYMBOLS = {
    "XAUUSD": "XAUUSD",
    "BTCUSD": "BTCUSD",
    "NASDAQ": "US100", 
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY"
}

TF_MAP_FCS = {
    "D1": "1D",
    "H4": "4h",
    "H1": "1h",
    "M15": "15m"
}

MACRO_FCS = {
    "DXY": "DXY",      
    "OIL": "WTI",      
    "US10Y": "US10Y"   
}

def fetch_fcs_history(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    try:
        url = f"https://api-v4.fcsapi.com/forex/history?symbol={symbol}&period={interval}&access_key={FCS_KEY}"
        resp = httpx.get(url, timeout=20).json()
        
        if not resp.get("status") or "response" not in resp:
            error_msg = resp.get('msg', 'No data')
            raise ValueError(f"FCS Error [{symbol} {interval}]: {error_msg}")
            
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
        if df.empty: 
            raise ValueError(f"FCS Error [{symbol} {interval}]: Data kosong")
        
        df = df.sort_values("timestamps").reset_index(drop=True)
        return df
        
    except Exception as e:
        raise e

def fetch_all_data(symbol: str) -> dict:
    if not FCS_KEY:
        raise ValueError("API Key FCS API kosong di GitHub Secrets!")

    data_dict = {}
    fcs_sym = FCS_SYMBOLS.get(symbol.upper(), symbol)
    
    print(f"Fetching {symbol} from FCS API (Delay 22s per request)...")
    
    # 1. Narik Data Utama (4 Timeframe)
    for tf_name, interval in TF_MAP_FCS.items():
        try:
            df = fetch_fcs_history(fcs_sym, interval)
            if df is not None:
                data_dict[tf_name] = df
        except Exception as e:
            raise ValueError(f"Gagal narik data {tf_name} ({symbol}): {str(e)}")
        finally:
            # JEDA 22 DETIK BIAR NGGAK KENA RATE LIMIT (3 req/min)
            print(f"Jeda 22 detik sebelum request berikutnya...")
            time.sleep(22)
        
    if "D1" not in data_dict or "H4" not in data_dict:
        raise ValueError("Data Utama (D1/H4) gagal ditarik dari FCS API.")

    # 2. Narik Data Makro
    macro_data = {}
    for macro_key, macro_sym in MACRO_FCS.items():
        try:
            df_m = fetch_fcs_history(macro_sym, "1D")
            if df_m is not None and len(df_m) >= 2:
                change = ((df_m['close'].iloc[-1] - df_m['close'].iloc[-2]) / df_m['close'].iloc[-2]) * 100
                macro_data[macro_key] = {"price": round(float(df_m['close'].iloc[-1]), 2), "change_pct": round(float(change), 2)}
        except Exception as e:
            print(f"Macro {macro_key} gagal: {e}")
        finally:
            time.sleep(22) # Jeda lagi buat makro

    print("Data fetching dari FCS API selesai!")
    return {"main": data_dict, "macro": macro_data}
