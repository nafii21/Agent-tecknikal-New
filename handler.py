import os, argparse, httpx, json
import html
from datetime import datetime
from agent.snapshot import generate_snapshot
from agent.llm_layer import analyze
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
        except Exception as e: print(f"Gagal kirim foto: {e}")

def send_tg_text(text):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        try:
            httpx.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=30)
        except Exception as e: print(f"Gagal kirim teks: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--model", default="nemotron")
    parser.add_argument("--cmd")
    args = parser.parse_args()

    if not args.symbol: return

    try:
        send_tg_text(f"⏳ Menganalisa <b>{args.symbol}</b> (Visual Vision AI)...\nMohon tunggu.")
        
        # 1. Ambil data teks & dataframe
        snapshot_text, df_h1, sessions = generate_snapshot(args.symbol)
        
        # 2. Bikin gambar chart
        chart_file = generate_chart(df_h1, args.symbol)
        if not chart_file:
            send_tg_text("❌ Gagal membuat gambar chart.")
            return

        # 3. Kirim Gambar + Teks ke Vision AI
        decision = analyze(chart_file, snapshot_text)
        
        if "error" in decision:
            send_tg_text(f"❌ {decision['error']}")
            return

        status = decision.get("status", "WAIT")
        emoji = "🎯" if status == "ENTRY" else "⏱️" if status == "PREPARE" else "⏳"

        text = (
            f"🏛️ <b>[HERMES VISION - SMC]</b>\n"
            f"📊 Pair: <b>{args.symbol}</b>\n"
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
        
        # Kirim Gambar + Teks ke Telegram
        send_tg_photo(chart_file, text)

    except Exception as e:
        send_tg_text(f"❌ <b>System Error:</b>\n<code>{html.escape(str(e))}</code>")

if __name__ == "__main__":
    main()
