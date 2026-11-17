import os, argparse, httpx, json
import html
from datetime import datetime
from agent.snapshot import generate_snapshot
from agent.llm_layer import analyze

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_tg(text):
    if TOKEN and CHAT_ID:
        if len(text) > 4000: text = text[:4000] + "\n\n<i>... (dipotong)</i>"
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        try:
            httpx.post(url, json=payload, timeout=30)
        except Exception as e: print(f"❌ Gagal kirim: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--model", default="nemotron")
    parser.add_argument("--cmd")
    args = parser.parse_args()

    if not args.symbol: return

    try:
        send_tg(f"⏳ Menganalisa <b>{args.symbol}</b> (State Machine SMC)...\nMohon tunggu.")
        
        snapshot_text = generate_snapshot(args.symbol)
        decision = analyze(snapshot_text)
        
        if "error" in decision:
            send_tg(f"❌ {decision['error']}")
            return

        status = decision.get("status", "WAIT")
        emoji = "🎯" if status == "ENTRY" else "⏱️" if status == "PREPARE" else "⏳"

        text = (
            f"🏛️ <b>[HERMES 2.0 - SMC CONTEXT]</b>\n"
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
                f"💎 TP2: <code>{decision.get('tp2', '-')}</code>\n"
                f"📊 RR: <b>{decision.get('rr', '-')}</b>\n"
                f"⚡ <b>Trigger:</b> {html.escape(decision.get('trigger', '-'))}\n"
            )
        
        send_tg(text)

    except Exception as e:
        send_tg(f"❌ <b>System Error:</b>\n<code>{html.escape(str(e))}</code>")

if __name__ == "__main__":
    main()
