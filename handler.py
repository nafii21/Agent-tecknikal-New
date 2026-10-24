import os, argparse, httpx, json, pandas as pd
from datetime import datetime
from agent.data import fetch_all_data
from agent.snapshot import generate_snapshot
from agent.llm_layer import analyze
from agent.memory import get_memory_summary, add_setup # <--- Import Memori

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

    if not args.symbol: return

    try:
        if args.cmd != "cron":
            send_tg(f"⏳ Menganalisa <b>{args.symbol}</b> (Dynamic Entry + Memory)...\nMohon tunggu.")
        
        # 1. Ambil Memory
        memory_summary = get_memory_summary(args.symbol)
        
        # 2. Ambil Data & Snapshot
        raw_data = fetch_all_data(args.symbol)
        snapshot_text = generate_snapshot(args.symbol, raw_data)
        
        # 3. Analisa AI (Dengan Memory)
        decision = analyze(snapshot_text, memory_summary)
        
        if "error" in decision:
            if args.cmd != "cron": send_tg(f"❌ {decision['error']}")
            return

        # 4. Simpan Log
        os.makedirs("log_analisa", exist_ok=True)
        time_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"log_analisa/{time_str}.md"
        
        with open(filename, "w") as f:
            f.write(f"# Analisa {args.symbol} - {time_str}\n\n")
            f.write(f"## Memory Feedback\n{memory_summary}\n\n")
            f.write(f"## Narrative\n{decision.get('narrative')}\n\n")
            f.write(f"## Setup Daily\n{json.dumps(decision.get('setup_daily'), indent=2)}\n\n")
            f.write(f"## Setup Session\n{json.dumps(decision.get('setup_session'), indent=2)}\n\n")

        daily = decision.get("setup_daily", {})
        session = decision.get("setup_session", {})
        
        # 5. Simpan Setup ke Memory (Kalau ada action)
        if daily.get("action") in ["BUY_LIMIT", "SELL_LIMIT"]:
            add_setup(args.symbol, "Daily", daily.get("action"), daily.get("entry_zone_min"), daily.get("entry_zone_max"), daily.get("sl"), daily.get("tp1"), daily.get("tp2"))
            
        if session.get("action") in ["BUY_LIMIT", "SELL_LIMIT"]:
            add_setup(args.symbol, "Session", session.get("action"), session.get("entry_zone_min"), session.get("entry_zone_max"), session.get("sl"), session.get("tp1"), session.get("tp2"))

        # 6. Kirim Telegram (Cek WAIT buat Cron)
        if args.cmd == "cron" and daily.get("action") == "WAIT" and session.get("action") == "WAIT":
            print("Cron: Tidak ada setup valid.")
            return

        def format_plan(plan, title):
            if plan.get("action") == "WAIT": return f"⏳ <b>{title}:</b> WAIT\n"
            return (
                f"🎯 <b>{title}:</b>\n"
                f"Action: <b>{plan.get('action')}</b>\n"
                f"📍 Zona Entry: {plan.get('entry_zone_min')} - {plan.get('entry_zone_max')}\n"
                f"🛑 SL: {plan.get('sl')} | 💎 TP1: {plan.get('tp1')} | TP2: {plan.get('tp2')}\n"
                f"⚡ <b>Trigger:</b> {plan.get('trigger_entry')}\n"
                f"⚠️ <b>Batal Jika:</b> {plan.get('dynamic_invalidation')}\n"
            )

        text = (
            f"🏛️ <b>[INSTITUTIONAL AI + MEMORY]</b>\n"
            f"📊 Pair: <b>{args.symbol}</b> | Bias: <b>{decision.get('bias', '-')}</b>\n"
            f"🕒 <b>Sesi:</b> {decision.get('session_analysis', '-')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧠 <b>Narrative:</b>\n{decision.get('narrative', '-')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{format_plan(daily, 'SETUP 1: DAILY INTRADAY')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{format_plan(session, 'SETUP 2: SESSION MOMENTUM')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 <i>Log: {filename}</i>"
        )
        
        send_tg(text)

    except Exception as e:
        if args.cmd != "cron": send_tg(f"❌ Gagal: {str(e)}")

if __name__ == "__main__":
    main()
