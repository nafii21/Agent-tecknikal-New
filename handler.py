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
        if len(text) > 4000: text = text[:4000] + "\n\n<i>... (dipotong)</i>"
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        try:
            resp = httpx.post(url, json=payload, timeout=30)
            if not resp.is_success:
                print(f"❌ Telegram Nolak Pesan: {resp.text}")
                payload.pop("parse_mode") 
                httpx.post(url, json=payload, timeout=30)
        except Exception as e: print(f"❌ Gagal kirim: {e}")

# --- FUNGSI BARU: KIRIM GAMBAR ---
def send_photo(photo_path, caption):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        try:
            with open(photo_path, "rb") as f:
                files = {"photo": f}
                data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
                httpx.post(url, data=data, files=files, timeout=30)
        except Exception as e: print(f"❌ Gagal kirim foto: {e}")

# --- FUNGSI BARU: KIRIM FILE CSV ---
def send_document(doc_path, caption):
    if TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
        try:
            with open(doc_path, "rb") as f:
                files = {"document": f}
                data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
                httpx.post(url, data=data, files=files, timeout=30)
        except Exception as e: print(f"❌ Gagal kirim dokumen: {e}")

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
            send_tg("📖 Belum ada catatan journal.")
            return
        total = len(history)
        wins = sum(1 for x in history if "WIN" in x.get('status', ''))
        losses = sum(1 for x in history if "LOSS" in x.get('status', ''))
        winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        txt = f"📊 <b>PERFORMA (Total: {total})</b>\n✅ Win: <b>{wins}</b> | ❌ Loss: <b>{losses}</b> | 🎯 WR: <b>{winrate:.1f}%</b>\n━━━━━━━━━━━━━━━━━━\n📖 <b>5 Terakhir:</b>\n"
        for r in history[:5]:
            txt += f"\n📅 {r.get('timestamp', '-')[:16]} WIB | 🧠 {r.get('model', 'Unknown').upper()}\n💱 {r.get('symbol')} | {r.get('plan_type')} | {r.get('action')}\n🏆 Status: <b>{r.get('status')}</b>\n"
        send_tg(txt)
        return

    # --- FITUR STATISTIK & CSV ---
    if args.cmd == "stats":
        from agent.report import export_csv, generate_wr_chart
        send_tg("⏳ Membuat Grafik & File CSV...")
        csv_file = export_csv()
        chart_file = generate_wr_chart()
        if not csv_file and not chart_file:
            send_tg("📊 Belum ada data untuk diekspor.")
            return
        if chart_file: 
            send_photo(chart_file, "📊 <b>Grafik Winrate Forward Test</b>")
        if csv_file: 
            send_document(csv_file, "📁 <b>Data Forward Test (CSV)</b>")
        return

    # --- FITUR ANALISA MARKET ---
    if not args.symbol: return

    try:
        memory_summary = get_memory_summary(args.symbol, args.model)
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
            add_setup(args.symbol, "Daily", daily.get("action"), daily.get("entry_zone_min"), daily.get("entry_zone_max"), daily.get("sl"), daily.get("tp1"), daily.get("tp2"), model=args.model)
            
        if session.get("action") in ["BUY_LIMIT", "SELL_LIMIT"]:
            add_setup(args.symbol, "Session", session.get("action"), session.get("entry_zone_min"), session.get("entry_zone_max"), session.get("sl"), session.get("tp1"), session.get("tp2"), model=args.model)

        def format_plan(plan, title):
            if plan.get("action") == "WAIT": 
                return f"⏳ <b>{title}</b>\n└ Status: WAIT (Tidak ada setup valid)\n"
            return (
                f"🎯 <b>{title}</b>\n├ Action: <b>{plan.get('action')}</b>\n"
                f"├ Zona Entry: <code>{plan.get('entry_zone_min')} - {plan.get('entry_zone_max')}</code>\n"
                f"├ SL: <code>{plan.get('sl')}</code>\n├ TP1: <code>{plan.get('tp1')}</code>\n├ TP2: <code>{plan.get('tp2')}</code>\n"
                f"├ ⚡ <b>Trigger:</b> <i>{clean_html(plan.get('trigger_entry'))}</i>\n"
                f"└ ⚠️ <b>Batal:</b> <i>{clean_html(plan.get('dynamic_invalidation'))}</i>\n"
            )

        header_title = "AUTO-SCAN SESI" if args.cmd == "cron" else "MANUAL REQUEST"

        text = (
            f"🏛️ <b>[HERMES AI - {header_title}]</b>\n"
            f"📊 <b>Pair:</b> {args.symbol} | 🧠 <b>Model:</b> {args.model.upper()}\n"
            f"📉 <b>Bias:</b> {decision.get('bias', '-')}\n"
            f"🕒 <b>Sesi:</b> {clean_html(decision.get('session_analysis', '-'))}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧠 <b>NARRATIVE:</b>\n<blockquote>{clean_html(decision.get('narrative', '-'))}</blockquote>\n"
            f"📌 <b>KEY LEVELS:</b>\n<blockquote>{clean_html(decision.get('key_levels', '-'))}</blockquote>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{format_plan(daily, 'SETUP 1: DAILY INTRADAY')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{format_plan(session, 'SETUP 2: SESSION MOMENTUM')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📝 <i>Log: {filename}</i>"
        )
        send_tg(text)

    except Exception as e:
        error_msg = str(e)
        if args.cmd != "cron": 
            send_tg(f"❌ <b>Data / System Error:</b>\n<code>{error_msg[:1000]}</code>")

if __name__ == "__main__":
    main()
