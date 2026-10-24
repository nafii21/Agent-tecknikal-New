import json, os
from datetime import datetime
import pandas as pd
import yfinance as yf

HISTORY_FILE = "trades_history.json"

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    try:
        with open(HISTORY_FILE, "r") as f: return json.load(f)
    except: return []

def save_history(data):
    with open(HISTORY_FILE, "w") as f: json.dump(data, f, indent=2)

def add_setup(symbol, plan_type, action, entry_min, entry_max, sl, tp1, tp2):
    data = load_history()
    setup = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "plan_type": plan_type, # "Daily" atau "Session"
        "action": action,
        "entry_min": float(entry_min),
        "entry_max": float(entry_max),
        "sl": float(sl),
        "tp1": float(tp1),
        "tp2": float(tp2),
        "status": "PENDING"
    }
    data.insert(0, setup)
    save_history(data)

def update_statuses(symbol):
    data = load_history()
    updated = False
    now = datetime.utcnow()
    
    # Tarik data M5 terbaru buat ngecek harga
    try:
        ticker = {"XAUUSD": "GC=F", "BTCUSD": "BTC-USD", "NASDAQ": "NQ=F"}.get(symbol, symbol)
        df = yf.download(ticker, period="5d", interval="5m", progress=False)
        if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)
        df = df.reset_index().rename(columns={"Datetime": "time"})
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)
    except:
        return

    for entry in data:
        if entry['symbol'] == symbol and entry['status'] == 'PENDING':
            entry_time = pd.to_datetime(entry['timestamp'])
            # Batasi cek maksimal 24 jam ke belakang
            if (now - entry_time).total_seconds() > 86400:
                entry['status'] = 'EXPIRED'
                updated = True
                continue

            df_after = df[df['time'] >= entry_time]
            if df_after.empty: continue

            action = entry['action']
            e_min, e_max = entry['entry_min'], entry['entry_max']
            sl, tp1 = entry['sl'], entry['tp1']
            
            is_triggered = False
            hit_status = None

            for _, row in df_after.iterrows():
                high, low = float(row['high']), float(row['low'])
                
                # 1. Cek Entry
                if not is_triggered:
                    if action == "BUY_LIMIT" and low <= e_min:
                        is_triggered = True
                    elif action == "SELL_LIMIT" and high >= e_max:
                        is_triggered = True
                    # Cek Missed (Kena TP duluan sebelum Entry)
                    elif action == "BUY_LIMIT" and high >= tp1:
                        hit_status = "MISSED (TP Before Entry)"
                        break
                    elif action == "SELL_LIMIT" and low <= tp1:
                        hit_status = "MISSED (TP Before Entry)"
                        break

                # 2. Cek TP/SL setelah Entry
                if is_triggered:
                    if action == "BUY_LIMIT":
                        if high >= tp1: hit_status = "WIN (TP HIT)"; break
                        elif low <= sl: hit_status = "LOSS (SL HIT)"; break
                    elif action == "SELL_LIMIT":
                        if low <= tp1: hit_status = "WIN (TP HIT)"; break
                        elif high >= sl: hit_status = "LOSS (SL HIT)"; break

            if hit_status:
                entry['status'] = hit_status
                updated = True

    if updated:
        save_history(data)

def get_memory_summary(symbol):
    update_statuses(symbol)
    data = load_history()
    
    # Filter khusus pair ini
    pair_data = [x for x in data if x['symbol'] == symbol and x['status'] != 'PENDING']
    
    if not pair_data:
        return "Belum ada histori trade yang selesai untuk pair ini."

    total = len(pair_data)
    wins = sum(1 for x in pair_data if "WIN" in x['status'])
    losses = sum(1 for x in pair_data if "LOSS" in x['status'])
    missed = sum(1 for x in pair_data if "MISSED" in x['status'])
    
    winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    # Breakdown per Plan
    daily_data = [x for x in pair_data if x['plan_type'] == 'Daily' and x['status'] in ['WIN (TP HIT)', 'LOSS (SL HIT)']]
    session_data = [x for x in pair_data if x['plan_type'] == 'Session' and x['status'] in ['WIN (TP HIT)', 'LOSS (SL HIT)']]
    
    daily_wr = (sum(1 for x in daily_data if "WIN" in x['status']) / len(daily_data) * 100) if daily_data else 0
    session_wr = (sum(1 for x in session_data if "WIN" in x['status']) / len(session_data) * 100) if session_data else 0

    summary = f"""
[MEMORI PERFORMA {symbol}]
- Total Trade Selesai: {total}
- Winrate Keseluruhan: {winrate:.1f}% (Win: {wins}, Loss: {losses}, Missed: {missed})
- Winrate Setup Daily: {daily_wr:.1f}%
- Winrate Setup Session: {session_wr:.1f}%

[CATATAN UNTUK AI]
Gunakan data winrate di atas! 
- Jika winrate Daily lebih tinggi, prioritaskan Setup Daily.
- Jika winrate Session rendah, berikan syarat trigger yang lebih ketat untuk Session.
- Pelajari status 'MISSED' (harga kena TP tapi nggak nyentuh Entry), jangan taruh Entry terlalu jauh dari harga saat ini.
"""
    return summary
