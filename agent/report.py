import json
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Biar bisa jalan di server tanpa layar
import matplotlib.pyplot as plt

HISTORY_FILE = "trades_history.json"

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    try:
        with open(HISTORY_FILE, "r") as f: return json.load(f)
    except: return []

def export_csv() -> str:
    history = load_history()
    if not history: return None
    
    df = pd.DataFrame(history)
    # Rapihin urutan kolom
    cols = ["timestamp", "symbol", "model", "plan_type", "action", "entry_min", "entry_max", "sl", "tp1", "tp2", "status"]
    df = df[[c for c in cols if c in df.columns]]
    
    csv_path = "trades_history.csv"
    df.to_csv(csv_path, index=False)
    return csv_path

def generate_wr_chart() -> str:
    history = load_history()
    if not history: return None
    
    status_counts = {"WIN": 0, "LOSS": 0, "MISSED": 0, "PENDING": 0, "EXPIRED": 0}
    for item in history:
        status = item.get("status", "PENDING")
        if "WIN" in status: status_counts["WIN"] += 1
        elif "LOSS" in status: status_counts["LOSS"] += 1
        elif "MISSED" in status: status_counts["MISSED"] += 1
        elif status == "EXPIRED": status_counts["EXPIRED"] += 1
        else: status_counts["PENDING"] += 1
        
    labels, sizes, colors = [], [], []
    color_map = {"WIN": "#00e676", "LOSS": "#ef5350", "MISSED": "#ffb300", "PENDING": "#29b6f6", "EXPIRED": "#757575"}

    for k, v in status_counts.items():
        if v > 0:
            labels.append(k)
            sizes.append(v)
            colors.append(color_map.get(k, "#cccccc"))

    if not sizes: return None

    # Bikin Grafik Donut
    plt.figure(figsize=(8, 6), facecolor='#121212')
    ax = plt.axes()
    ax.set_facecolor('#121212')
    
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%',
           textprops={'color': "w", 'fontsize': 12}, startangle=140)
    
    # Bikin lubang di tengah (Donut)
    centre_circle = plt.Circle((0,0),0.70,fc='#121212')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    
    # Hitung Winrate
    wins, losses = status_counts["WIN"], status_counts["LOSS"]
    total_closed = wins + losses
    wr = (wins / total_closed * 100) if total_closed > 0 else 0
    
    # Tulis Winrate di tengah
    plt.text(0, 0, f"WR\n{wr:.1f}%", ha='center', va='center', fontsize=24, color='#00e676' if wr >= 50 else '#ef5350', weight='bold')
    plt.title("Forward Test Results", color='white', fontsize=16)
    
    chart_path = "winrate_chart.png"
    plt.savefig(chart_path, bbox_inches='tight', dpi=150, facecolor='#121212')
    plt.close()
    return chart_path
