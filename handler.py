import os, argparse, httpx, json, pandas as pd
import html
from datetime import datetime
from agent.data import fetch_all_data
from agent.snapshot import generate_snapshot
from agent.llm_layer import analyze_deepseek, analyze_nemotron
from agent.memory import get_memory_summary, add_setup, load_history

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def clean_html(text):
    if not text: return "-"
    return str(text).replace("<", "&lt;").replace(">", "&gt;")

def send_tg(text):
    if TOKEN and CHAT_ID:
        if len(text) > 4000:
            text = text[:4000] + "\n\n<i>... (Pesan dipotong)</i>"
            
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        
        try:
            resp = httpx.post(url, json=payload, timeout=30)
            if not resp.is_success:
                print(f"❌ Telegram Nolak Pesan: {resp.text}")
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

    # --- FITUR JOURNAL ---
    if args.cmd == "journal":
        history = load_history()
        if not history:
            send_tg("📖 Belum ada catatan journal (trades_history.json kosong).")
            return
        
        # Itung Statistik
        total = len(history)
        wins = sum(1 for x in history if "WIN" in x.get('status', ''))
        losses = sum(1 for x in history if "LOSS" in x.get('status', ''))
        missed = sum(1 for x in history if "MISSED" in x.get('status', ''))
        pending = sum(1 for x in history if x.get('status') == 'PENDING')
        expired = sum(1 for x in history if x.get('status') == 'EXPIRED')
        
        closed = wins + losses
        winrate = (wins / closed * 100) if closed > 0 else 0
        
        txt = (
            f"📊 <b>PERFORMA TRADING (Total: {total})</b>\n"
            f"✅ Win: <b>{wins}</b> | ❌ Loss: <b>{losses}</b> | ⏳ Pending: <b>{pending}</b>\n"
            f"⚠️ Missed: {missed} | ⏰ Expired: {expired}\n"
            f"🎯 Winrate: <b>{winrate:.1f}%</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📖 <b>5 Catatan Journal Terakhir:</b>\n"
        )
        
        for r in history[:5]: # Ambil 5 teratas
            txt += (
                f"\n📅 {r.get('timestamp', '-')[:16]} WIB\n"
                f"💱 {r.get('symbol', '-')} | {r.get('plan_type', '-')} | {r.get('action', '-')}\n"
                f"📍 Entry: {r.get('entry_min', '-')} - {r.get('entry_max', '-')}\n"
                f"🛑 SL: {r.get('sl', '-')} | 💎 TP: {r.get('tp1', '-')}\n"
                f"🏆 Status: <b>{r.get('status', '-')}</b>\n"
                f"━━━━━━━━━━━━━━━━━━"
            )
        send_tg(txt)
        return

    # --- FITUR ANALISA MARKET ---
    if not args.symbol: return

    try:
        memory_summary = get_memory_summary(args.symbol)
        raw_data = fetch_all_data(args.symbol)
        snapshot_text = generate_snapshot(args.symbol, raw_data)
        
        if args.model.lower() == "nemotron":
            decision = analyze_nemotron(snapshot_text, memory_summary)
        else:
            decision = analyze_deepseek(snapshot_text, memory_summary)
        
        if "error" in decision:
            if args.cmd != "cron": send_tg(f"❌ {decision['error']}")
            return

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
        
        if daily.get("action") in ["BUY_LIMIT", "SELL_LIMIT"]:
            add_setup(args.symbol, "Daily", daily.get("action"), daily.get("entry_zone_min"), daily.get("entry_zone_max"), daily.get("sl"), daily.get("tp1"), daily.get("tp2"))
            
        if session.get("action") in ["BUY_LIMIT", "SELL_LIMIT"]:
            add_setup(args.symbol, "Session", session.get("action"), session.get("entry_zone_min"), session.get("entry_zone_max"), session.get("sl"), session.get("tp1"), session.get("tp2"))

        if args.cmd == "cron" and daily.get("action") == "WAIT" and session.get("action") == "WAIT":
            print("Cron: Tidak ada setup valid.")
            return

        # --- FORMATTING TELEGRAM ---
        def format_plan(plan, title):
            if plan.get("action") == "WAIT": 
                return f"⏳ <b>{title}</b>\n└ Status: WAIT\n"
                
            return (
                f"🎯 <b>{title}</b>\n"
                f"├ Action: <b>{plan.get('action')}</b>\n"
                f"├ Zona Entry: <code>{plan.get('entry_zone_min')} - {plan.get('entry_zone_max')}</code>\n"
                f"├ SL: <code>{plan.get('sl')}</code>\n"
                f"├ TP1: <code>{plan.get('tp1')}</code>\n"
                f"├ TP2: <code>{plan.get('tp2')}</code>\n"
                f"├ ⚡ <b>Trigger:</b> <i>{clean_html(plan.get('trigger_entry'))}</i>\n"
                f"└ ⚠️ <b>Batal:</b> <i>{clean_html(plan.get('dynamic_invalidation'))}</i>\n"
            )

        text = (
            f"🏛️ <b>[HERMES INSTITUTIONAL AI - {args.model.upper()}]</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Pair:</b> {args.symbol}\n"
            f"📉 <b>Bias:</b> {decision.get('bias', '-')}\n"
            f"🕒 <b>Sesi:</b> {clean_html(decision.get('session_analysis', '-'))}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧠 <b>NARRATIVE (Analisa):</b>\n"
            f"<blockquote>{clean_html(decision.get('narrative', '-'))}</blockquote>\n"
            f"📌 <b>KEY LEVELS:</b>\n"
            f"<blockquote>{clean_html(decision.get('key_levels', '-'))}</blockquote>\n"
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
