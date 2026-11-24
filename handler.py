import os, argparse, httpx, json
import html
from agent.snapshot import generate_snapshot
from agent.llm_layer import analyze_h1, analyze_m15, analyze_m5, analyze_m1
from agent.charting import generate_chart
from agent.exness_executor import place_limit_order # <--- Import Eksekutor

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_tg_photo(photo_path, caption):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        try:
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
                httpx.post(url, data=data, files=files, timeout=30)
        except Exception as e: print(f"Gagal foto: {e}")

def send_tg_text(text):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            httpx.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=30)
        except: pass

def format_signal(decision, tf_label):
    status = decision.get("status", "WAIT")
    emoji = "🎯" if status == "ENTRY" else "⏱️" if status == "PREPARE" else "⏳"
    
    text = (
        f"🏛️ <b>[HERMES VISION - {tf_label}]</b>\n"
        f"⚡ Status: <b>{emoji} {status}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🧠 <b>Context:</b>\n{html.escape(decision.get('context_reason', '-'))}\n\n"
        f"🎯 <b>Setup:</b> {decision.get('setup_type', '-')}\n"
        f"📉 <b>Bias:</b> {decision.get('bias', '-')}\n"
    )
    
    if status == "ENTRY":
        text += (
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📍 Entry: <code>{decision.get('entry', '-')}</code>\n"
            f"🛑 SL: <code>{decision.get('sl', '-')}</code>\n"
            f"💎 TP1: <code>{decision.get('tp1', '-')}</code>\n"
            f"📊 RR: <b>{decision.get('rr', '-')}</b>\n"
            f"⚡ <b>Trigger:</b> {html.escape(decision.get('trigger', '-'))}\n"
        )
    return text

def execute_to_exness(decision, symbol):
    """Fungsi buat ngeksekusi sinyal ke Exness"""
    action = decision.get("action", "") # BUY_LIMIT / SELL_LIMIT
    if action not in ["BUY_LIMIT", "SELL_LIMIT"]:
        return "\n\n❌ Eksekusi Exness dibatalkan: Action bukan Limit Order."
        
    entry = decision.get("entry", 0)
    sl = decision.get("sl", 0)
    tp = decision.get("tp1", 0)
    
    # Format simbol Exness (misal XAUUSD jadi XAUUSD)
    exness_symbol = symbol.upper() 
    
    res = place_limit_order(exness_symbol, action, entry, sl, tp, volume=0.01)
    
    if res.get("success"):
        return f"\n\n✅ <b>EXNESS ORDER SUKSES</b>\nOrder ID: <code>{res['order_id']}</code>\nLot: 0.01"
    else:
        return f"\n\n❌ <b>EXNESS ERROR:</b>\n<code>{html.escape(str(res.get('error')))}</code>"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    args = parser.parse_args()

    if not args.symbol: return
    symbol = args.symbol

    try:
        # 1. Ambil Data & Gambar H1
        send_tg_text(f"⏳ Analisa H1 untuk <b>{symbol}</b>...")
        snapshot_text, df_h1, df_m15, df_m5, df_m1, sessions = generate_snapshot(symbol)
        chart_h1 = generate_chart(df_h1, symbol, "H1")
        
        decision_h1 = analyze_h1(chart_h1, snapshot_text)
        
        # --- ALUR 1: H1 SETUP -> KONFIRMASI M5 ---
        if decision_h1.get("status") in ["PREPARE", "ENTRY"]:
            send_tg_text("⏱️ H1 nemu setup! Turun ke M5 untuk konfirmasi trigger...")
            chart_m5 = generate_chart(df_m5, symbol, "M5")
            
            h1_context = decision_h1.get('context_reason', 'Setup di H1')
            m5_text_data = f"{snapshot_text}\n\n[KONTEKS DARI H1]:\n{h1_context}"
            
            decision_m5 = analyze_m5(chart_m5, m5_text_data)
            final_caption = format_signal(decision_m5, "M5 Trigger")
            
            if decision_m5.get("status") == "ENTRY":
                # Tembak Exness!
                exec_msg = execute_to_exness(decision_m5, symbol)
                final_caption += exec_msg
                
            send_tg_photo(chart_m5, final_caption)
            return

        # --- ALUR 2: H1 WAIT -> M15 -> M1 ---
        send_tg_text("⏳ H1 WAIT. Turun ke M15 cari likuiditas...")
        chart_m15 = generate_chart(df_m15, symbol, "M15")
        decision_m15 = analyze_m15(chart_m15, snapshot_text)
            
        if decision_m15.get("status") in ["PREPARE", "ENTRY"]:
            send_tg_text("⏱️ M15 nemu Sweep/POI! Turun ke M1 untuk sniper trigger...")
            chart_m1 = generate_chart(df_m1, symbol, "M1")
            
            m15_context = decision_m15.get('context_reason', 'Sweep terdeteksi')
            m1_text_data = f"{snapshot_text}\n\n[KONTEKS DARI M15]:\n{m15_context}"
            
            decision_m1 = analyze_m1(chart_m1, m1_text_data)
            final_caption = format_signal(decision_m1, "M1 Trigger")
            
            if decision_m1.get("status") == "ENTRY":
                # Tembak Exness!
                exec_msg = execute_to_exness(decision_m1, symbol)
                final_caption += exec_msg
                
            send_tg_photo(chart_m1, final_caption)
            return
            
        send_tg_photo(chart_m15, format_signal(decision_m15, "M15 Liquidity") + "\n\n<i>H1 & M15 belum ada setup. Sabar ya.</i>")

    except Exception as e:
        send_tg_text(f"❌ <b>System Error:</b>\n<code>{html.escape(str(e))}</code>")

if __name__ == "__main__":
    main()
