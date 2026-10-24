import os, argparse, httpx, json, pandas as pd
from datetime import datetime
from agent.data import fetch_all_data
from agent.snapshot import generate_snapshot
from agent.llm_layer import analyze

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_tg(text):
    if TOKEN and CHAT_ID:
        httpx.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=30)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--tf") 
    parser.add_argument("--cmd")
    args = parser.parse_args()

    if not args.symbol:
        send_tg("❌ Pair kosong.")
        return

    try:
        if args.cmd != "cron":
            send_tg(f"⏳ Menganalisa <b>{args.symbol}</b> (MTF + Fundamental)...\nMohon tunggu 1-2 menit.")
        
        # 1. Ambil Data
        raw_data = fetch_all_data(args.symbol)
        
        # 2. Bikin Snapshot
        snapshot_text = generate_snapshot(args.symbol, raw_data)
        
        # 3. Analisa AI
        decision = analyze(snapshot_text)
        
        if "error" in decision:
            if args.cmd != "cron": send_tg(f"❌ {decision['error']}")
            return

        # 4. Bikin Log Markdown (.md)
        os.makedirs("log_analisa", exist_ok=True)
        time_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"log_analisa/{time_str}.md"
        
        with open(filename, "w") as f:
            f.write(f"# Analisa {args.symbol} - {time_str}\n\n")
            f.write(f"## Session\n{decision.get('session_analysis')}\n\n")
            f.write(f"## Narrative\n{decision.get('narrative')}\n\n")
            f.write(f"## Key Levels\n{decision.get('key_levels')}\n\n")
            f.write(f"## Plan A\n{json.dumps(decision.get('plan_a'), indent=2)}\n\n")
            f.write(f"## Plan B\n{json.dumps(decision.get('plan_b'), indent=2)}\n\n")
            f.write(f"## Raw Snapshot\n```\n{snapshot_text}\n```\n")

        # 5. Cek WAIT buat Cron
        plan_a = decision.get("plan_a", {})
        plan_b = decision.get("plan_b", {})
        
        is_wait_a = plan_a.get("action") == "WAIT"
        is_wait_b = plan_b.get("action") == "WAIT"

        if args.cmd == "cron" and is_wait_a and is_wait_b:
            print("Cron: Tidak ada setup valid. Notifikasi tidak dikirim.")
            return

        # 6. Format Telegram (Dengan Key Levels & Trigger)
        text = (
            f"🏛️ <b>[INSTITUTIONAL FUND MANAGER]</b>\n"
            f"📊 Pair: <b>{args.symbol}</b>\n"
            f"📉 Bias: <b>{decision.get('bias', '-')}</b>\n"
            f"🕒 <b>Sesi:</b> {decision.get('session_analysis', '-')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧠 <b>Narrative:</b>\n{decision.get('narrative', '-')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Key Levels:</b>\n{decision.get('key_levels', '-')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>PLAN A (Utama):</b>\n"
            f"Action: {plan_a.get('action')}\n"
            f"Entry: {plan_a.get('entry')} | SL: {plan_a.get('sl')}\n"
            f"TP1: {plan_a.get('tp1')} | TP2: {plan_a.get('tp2')}\n"
            f"⚡ Trigger: {plan_a.get('trigger_entry', '-')}\n"
            f"Batal jika: {plan_a.get('invalidation')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 <b>PLAN B (Cadangan):</b>\n"
            f"Action: {plan_b.get('action')}\n"
            f"Entry: {plan_b.get('entry')} | SL: {plan_b.get('sl')}\n"
            f"TP1: {plan_b.get('tp1')} | TP2: {plan_b.get('tp2')}\n"
            f"⚡ Trigger: {plan_b.get('trigger_entry', '-')}\n"
            f"Batal jika: {plan_b.get('invalidation')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 <i>Log tersimpan di {filename}</i>"
        )
        
        send_tg(text)

    except Exception as e:
        if args.cmd != "cron": send_tg(f"❌ Gagal: {str(e)}")

if __name__ == "__main__":
    main()
