import os, argparse, httpx, json
import html
from agent.snapshot import generate_snapshot
from agent.llm_layer import analyze_h1, analyze_m15, analyze_m1
from agent.charting import generate_chart

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--model", required=False) 
    parser.add_argument("--cmd", required=False)
    args = parser.parse_args()

    if not args.symbol: return

    try:
        # 1. H1 Context
        send_tg_text(f"⏳ Analisa H1 untuk <b>{args.symbol}</b>...")
        snapshot_text, df_h1, df_m15, df_m1, sessions = generate_snapshot(args.symbol)
        chart_h1 = generate_chart(df_h1, args.symbol, "H1")
        
        decision_h1 = analyze_h1(chart_h1, snapshot_text)
        if "error" in decision_h1:
            send_tg_text(f"❌ H1 Error: {decision_h1['error']}")
            return

        if decision_h1.get("status") in ["PREPARE", "ENTRY"]:
            send_tg_photo(chart_h1, format_signal(decision_h1, "H1 Context"))
            return

        # 2. M15 Liquidity
        send_tg_text("⏳ H1 WAIT. Turun ke M15 cari likuiditas...")
        chart_m15 = generate_chart(df_m15, args.symbol, "M15")
        
        decision_m15 = analyze_m15(chart_m15, snapshot_text)
        if "error" in decision_m15:
            send_tg_text(f"❌ M15 Error: {decision_m15['error']}")
            return
            
        if decision_m15.get("status") == "WAIT":
            send_tg_photo(chart_m15, format_signal(decision_m15, "M15 Liquidity") + "\n\n<i>H1 & M15 belum ada setup. Sabar ya.</i>")
            return

        # 3. M1 Trigger (Kirim Konteks M15 ke M1)
        send_tg_text("⏱️ M15 nemu Sweep/POI! Turun ke M1 untuk sniper trigger...")
        chart_m1 = generate_chart(df_m1, args.symbol, "M1")
        
        # --- SUNTIK KONTEKS M15 KE DALAM DATA M1 ---
        m15_context = decision_m15.get('context_reason', 'Sweep terdeteksi di M15')
        m1_text_data = f"{snapshot_text}\n\n[KONTEKS DARI M15]:\n{m15_context}\nGunakan likuiditas M15 ini sebagai target TP."
        
        decision_m1 = analyze_m1(chart_m1, m1_text_data)
        if "error" in decision_m1:
            send_tg_text(f"❌ M1 Error: {decision_m1['error']}")
            return
            
        final_caption = format_signal(decision_m1, "M1 Trigger")
        send_tg_photo(chart_m1, final_caption)

    except Exception as e:
        send_tg_text(f"❌ <b>System Error:</b>\n<code>{html.escape(str(e))}</code>")

if __name__ == "__main__":
    main()
