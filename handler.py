import os, argparse, httpx, json
import html
from agent.snapshot import generate_snapshot
from agent.llm_layer import analyze_h1, analyze_m15
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
    args = parser.parse_args()

    if not args.symbol: return

    try:
        send_tg_text(f"⏳ Menganalisa <b>{args.symbol}</b> (H1 Context)...")
        
        # 1. Ambil data & Gambar H1
        snapshot_text, df_h1, df_m15, sessions = generate_snapshot(args.symbol)
        chart_h1 = generate_chart(df_h1, args.symbol, "H1")
        
        if not chart_h1: raise ValueError("Gagal bikin chart H1")
        
        # 2. Analisa H1
        decision_h1 = analyze_h1(chart_h1, snapshot_text)
        if "error" in decision_h1:
            send_tg_text(f"❌ H1 Error: {decision_h1['error']}")
            return

        # 3. Cek Status H1
        if decision_h1.get("status") in ["PREPARE", "ENTRY"]:
            # Kalau H1 udah bagus, kirim chart H1
            send_tg_photo(chart_h1, format_signal(decision_h1, "H1 Context"))
        else:
            # 4. Kalau H1 WAIT, Turun ke M15!
            send_tg_text("⏳ H1 WAIT. Turun ke M15 untuk cari likuiditas...")
            
            chart_m15 = generate_chart(df_m15, args.symbol, "M15")
            if not chart_m15: raise ValueError("Gagal bikin chart M15")
            
            decision_m15 = analyze_m15(chart_m15, snapshot_text)
            if "error" in decision_m15:
                send_tg_text(f"❌ M15 Error: {decision_m15['error']}")
                return
            
            # Kirim hasil analisa M15
            caption_m15 = format_signal(decision_m15, "M15 Liquidity")
            if decision_m15.get("status") == "WAIT":
                # Kalau M15 juga WAIT, kasih tau alasannya
                caption_m15 += "\n\n<i>H1 dan M15 belum ada setup. Sabar ya bro.</i>"
            
            send_tg_photo(chart_m15, caption_m15)

    except Exception as e:
        send_tg_text(f"❌ <b>System Error:</b>\n<code>{html.escape(str(e))}</code>")

if __name__ == "__main__":
    main()
