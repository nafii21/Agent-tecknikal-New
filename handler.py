import os, argparse, httpx, json, pandas as pd
import html
from datetime import datetime
from agent.data import fetch_all_data
from agent.snapshot import generate_snapshot
from agent.llm_layer import analyze_deepseek, analyze_nemotron
from agent.memory import get_memory_summary, add_setup

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def clean_html(text):
    """Ngubah < jadi &lt; dan > jadi &gt; biar nggak dianggap tag HTML sama Telegram"""
    if not text: return "-"
    return str(text).replace("<", "&lt;").replace(">", "&gt;")

def send_tg(text):
    if TOKEN and CHAT_ID:
        # 1. Batasi panjang pesan (Telegram max 4096 char)
        if len(text) > 4000:
            text = text[:4000] + "\n\n<i>... (Pesan dipotong karena terlalu panjang)</i>"
            
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        
        try:
            # 2. Kirim pesan & cek respon
            resp = httpx.post(url, json=payload, timeout=30)
            if not resp.is_success:
                print(f"❌ Telegram Nolak Pesan: {resp.text}")
                # 3. Kalau ditolak gara-gara HTML, kirim ulang tanpa HTML
                payload.pop("parse_mode") 
                httpx.post(url, json=payload, timeout=30)
        except Exception as e:
            print(f"❌ Gagal kirim ke Telegram: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--model", default="deepseek")
    parser.add_argument("--cmd")
    args = parser.parse_args()

    if not args.symbol: return

    try:
        # 1. Ambil Memory
        memory_summary = get_memory_summary(args.symbol)
        
        # 2. Ambil Data & Snapshot
        raw_data = fetch_all_data(args.symbol)
        snapshot_text = generate_snapshot(args.symbol, raw_data)
        
        # 3. Routing Model AI
        if args.model.lower() == "nemotron":
            decision = analyze_nemotron(snapshot_text, memory_summary)
        else:
            decision = analyze_deepseek(snapshot_text, memory_summary)
        
        if "error" in decision:
            if args.cmd != "cron": send_tg(f"❌ {decision['error']}")
            return

        # 4. Simpan Log Markdown
        os.makedirs("log_analisa", exist_ok=True)
        time_str = datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = f"log_analisa/{time_str}.md"
        
        with open(filename, "w") as f:
            f.write(f"# Analisa {args.symbol} (Model: {args.model.upper()}) - {time_str}\n\n")
            f.write(f"## Memory Feedback\n{memory_summary}\n\n")
            f.write(f"## Narrative\n{decision.get('narrative')}\n\n")
            f.write(f"## Key Levels\n{decision.get('key_levels')}\n\n")
            f.write(f"## Setup Daily\n{json.dumps(decision.get('setup_daily'), indent=2)}\n\n")
            f.write(f"## Setup Session\n{json.dumps(decision.get('setup_session'), indent=2)}\n\n")

        daily = decision.get("setup_daily", {})
        session = decision.get("setup_session", {})
        
        # 5. Simpan Setup ke Memory
        if daily.get("action") in ["BUY_LIMIT", "SELL_LIMIT"]:
            add_setup(args.symbol, "Daily", daily.get("action"), daily.get("entry_zone_min"), daily.get("entry_zone_max"), daily.get("sl"), daily.get("tp1"), daily.get("tp2"))
            
        if session.get("action") in ["BUY_LIMIT", "SELL_LIMIT"]:
            add_setup(args.symbol, "Session", session.get("action"), session.get("entry_zone_min"), session.get("entry_zone_max"), session.get("sl"), session.get("tp1"), session.get("tp2"))

        # 6. Cek WAIT
        if args.cmd == "cron" and daily.get("action") == "WAIT" and session.get("action") == "WAIT":
            print("Cron: Tidak ada setup valid.")
            return

        # 7. Format Telegram (Bersihkan HTML)
        def format_plan(plan, title):
            if plan.get("action") == "WAIT": return f"⏳ <b>{title}:</b> WAIT\n"
            return (
                f"🎯 <b>{title}:</b>\n"
                f"Action: <b>{plan.get('action')}</b>\n"
                f"📍 Zona Entry: {plan.get('entry_zone_min')} - {plan.get('entry_zone_max')}\n"
                f"🛑 SL: {plan.get('sl')} | 💎 TP1: {plan.get('tp1')} | TP2: {plan.get('tp2')}\n"
                f"⚡ <b>Trigger:</b> {clean_html(plan.get('trigger_entry'))}\n"
                f"⚠️ <b>Batal Jika:</b> {clean_html(plan.get('dynamic_invalidation'))}\n"
            )

        text = (
            f"🏛️ <b>[INSTITUTIONAL AI ({args.model.upper()})]</b>\n"
            f"📊 Pair: <b>{args.symbol}</b> | Bias: <b>{decision.get('bias', '-')}</b>\n"
            f"🕒 <b>Sesi:</b> {clean_html(decision.get('session_analysis', '-'))}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧠 <b>Narrative:</b>\n{clean_html(decision.get('narrative', '-'))}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>Key Levels:</b>\n{clean_html(decision.get('key_levels', '-'))}\n"
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
