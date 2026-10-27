import os, httpx, time
import pandas as pd
import logging

logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# --- KONFIGURASI FCS API ---
FCS_KEY = os.getenv("FCS_API_KEY")

# Mapping Simbol FCS API
FCS_SYMBOLS = {
    "XAUUSD": "XAUUSD",
    "BTCUSD": "BTCUSD",
    "NASDAQ": "NASDAQ", # Mungkin perlu disesuaikan (misal US100)
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY"
}

# Mapping Timeframe (FCS API: 15m, 1h, 4h, 1D)
TF_MAP_FCS = {
    "D1": "1D",
    "H4": "4h",
    "H1": "1h",
    "M15": "15m"
}

# Simbol Makro (Jika didukung FCS, jika tidak akan kosong)
MACRO_FCS = {
    "DXY": "DXY",      # Coba DXY
    "OIL": "WTI",      # Coba WTI
    "US10Y": "US10Y"   # Coba US10Y
}

def fetch_fcs_history(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    """Fungsi narik data historis dari FCS API"""
    try:
        url = f"https://api-v4.fcsapi.com/forex/history?symbol={symbol}&period={interval}&access_key={FCS_KEY}"
        resp = httpx.get(url, timeout=20).json()
        
        if not resp.get("status") or "response" not in resp:
            print(f"FCS API Error [{symbol} {interval}]: {resp.get('msg', 'No data')}")
            return None
            
        raw_data = resp["response"]
        records = []
        
        # Format respons FCS: { "timestamp": { "o":..., "h":..., "l":..., "c":... } }
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
        if df.empty: return None
        
        df = df.sort_values("timestamps").reset_index(drop=True)
        return df
        
    except Exception as e:
        print(f"FCS Request Error [{symbol} {interval}]: {e}")
        return None

def fetch_all_data(symbol: str) -> dict:
    if not FCS_KEY:
        raise ValueError("API Key FCS API kosong di GitHub Secrets!")

    data_dict = {}
    fcs_sym = FCS_SYMBOLS.get(symbol.upper(), symbol)
    
    print(f"Fetching {symbol} from FCS API...")
    
    # 1. Narik Data Utama (4 Timeframe)
    for tf_name, interval in TF_MAP_FCS.items():
        df = fetch_fcs_history(fcs_sym, interval)
        
        if df is not None:
            # Khusus H4, kita resample dari data 1h jika FCS ngasih 1h
            # TAPI FCS udah support 4h, jadi langsung pakai
            data_dict[tf_name] = df
        
        # Jeda 2 detik biar nggak kena rate limit (500 req/bulan)
        time.sleep(2)
        
    if "D1" not in data_dict or "H4" not in data_dict:
        raise ValueError("Data Utama (D1/H4) gagal ditarik dari FCS API. Cek limit atau API Key.")

    # 2. Narik Data Makro (Coba-coba, kalau gagal kosongin)
    macro_data = {}
    for macro_key, macro_sym in MACRO_FCS.items():
        df_m = fetch_fcs_history(macro_sym, "1D", limit=5)
        if df_m is not None and len(df_m) >= 2:
            change = ((df_m['close'].iloc[-1] - df_m['close'].iloc[-2]) / df_m['close'].iloc[-2]) * 100
            macro_data[macro_key] = {"price": round(float(df_m['close'].iloc[-1]), 2), "change_pct": round(float(change), 2)}
        
        time.sleep(2) # Jeda lagi

    print("Data fetching dari FCS API selesai!")
    return {"main": data_dict, "macro": macro_data}
