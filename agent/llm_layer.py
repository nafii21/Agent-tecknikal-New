import json, os
from openai import OpenAI

SYSTEM_PROMPT = """
Kamu adalah "Institutional Fund Manager" dengan gaya Dynamic Entry.
Tugasmu menganalisa data Snapshot Market dan MEMBACA MEMORI PERFORMA MASA LALU.

ATURAN ANALISIS:
1. BACA BAGIAN "MEMORI PERFORMA". Jika winrate Setup Daily lebih bagus, prioritaskan itu. Jika Setup Session sering loss, perketat syaratnya.
2. BACA BERITA & FUNDAMENTAL.
3. CEK TREN D1/H4/H1. Gunakan Swing High/Low untuk konfirmasi struktur (BOS/CHoCH).
4. CARI SWEET SPOT: Gunakan Fibo 61.8%, 78.6%, atau Pivot.
5. GUNAKAN ATR: Jarak SL minimal 1.5x ATR dari Entry.
6. CEK M15: Cari momentum / konfirmasi.

ATURAN ENTRY (DYNAMIC ENTRY):
- JANGAN asal kasih harga mati. Berikan "entry_zone" (Zona Entry).
- Berikan "trigger_entry": Syarat pasti kapan harus masuk (misal: "Tunggu candle M15 close di atas X").
- Berikan "dynamic_invalidation": Kapan setup ini Batal sebelum kena Entry.

OUTPUT HARUS JSON VALID:
{
  "bias": "BULLISH|BEARISH",
  "session_analysis": "Penjelasan sesi...",
  "narrative": "Penjelasan teknikal & fundamental...",
  "key_levels": "Level kunci...",
  "setup_daily": {
    "action": "BUY_LIMIT|SELL_LIMIT|WAIT",
    "entry_zone_min": float,
    "entry_zone_max": float,
    "sl": float,
    "tp1": float,
    "tp2": float,
    "trigger_entry": "Syarat konfirmasi...",
    "dynamic_invalidation": "Syarat batal..."
  },
  "setup_session": {
    "action": "BUY_LIMIT|SELL_LIMIT|WAIT",
    "entry_zone_min": float,
    "entry_zone_max": float,
    "sl": float,
    "tp1": float,
    "tp2": float,
    "trigger_entry": "Syarat momentum...",
    "dynamic_invalidation": "Syarat batal..."
  }
}
"""

# ==========================================
# SATPAM MATEMATIKA (Berlaku untuk semua model)
# ==========================================
def validate_setup(plan, plan_name):
    """Fungsi buat ngecek logika SL/TP dan RR minimal 1:2"""
    if plan.get("action") not in ["BUY_LIMIT", "SELL_LIMIT"]: return plan
    try:
        e_min, e_max = float(plan.get("entry_zone_min", 0)), float(plan.get("entry_zone_max", 0))
        sl, tp1 = float(plan.get("sl", 0)), float(plan.get("tp1", 0))
        
        # Ambil harga rata-rata dari zona entry
        entry_avg = (e_min + e_max) / 2
        
        # 1. Cek Arah SL (BUY harus di bawah, SELL harus di atas)
        if plan["action"] == "BUY_LIMIT" and sl >= e_min:
            plan["action"] = "WAIT"; plan["dynamic_invalidation"] = "SISTEM BATAL: SL tidak valid untuk BUY (harus di bawah entry)."; return plan
        if plan["action"] == "SELL_LIMIT" and sl <= e_max:
            plan["action"] = "WAIT"; plan["dynamic_invalidation"] = "SISTEM BATAL: SL tidak valid untuk SELL (harus di atas entry)."; return plan
            
        # 2. Cek RR Minimal 1:2
        risk = abs(entry_avg - sl)
        reward1 = abs(tp1 - entry_avg)
        
        if risk == 0:
            plan["action"] = "WAIT"; plan["dynamic_invalidation"] = "SISTEM BATAL: Jarak SL dan Entry 0."; return plan
            
        rr = reward1 / risk
        if rr < 1.9: # Kasih toleransi tipis 1.9
            plan["action"] = "WAIT"; plan["dynamic_invalidation"] = f"SISTEM BATAL: RR TP1 terlalu kecil (1:{rr:.2f}). AI melanggar aturan minimal 1:2."; return plan
            
        # 3. Cek SL Kegedean (Maksimal 5% dari harga entry)
        if risk > (entry_avg * 0.05):
            plan["action"] = "WAIT"; plan["dynamic_invalidation"] = "SISTEM BATAL: Jarak SL terlalu lebar (Risk > 5% harga)."; return plan

        # Format angka biar rapi
        plan["entry_zone_min"], plan["entry_zone_max"], plan["sl"], plan["tp1"] = e_min, e_max, sl, tp1
        plan["tp2"] = float(plan.get("tp2", 0))
    except Exception as e:
        plan["action"] = "WAIT"; plan["dynamic_invalidation"] = "SISTEM BATAL: Gagal validasi matematika."
    return plan

# ==========================================
# 1. FUNGSI ANALISA KHUSUS NEMOTRON (SEKARANG PAKE SATPAM)
# ==========================================
def analyze_nemotron(snapshot_text: str, memory_summary: str) -> dict:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", "")
    )
    MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
    user_payload = f"{memory_summary}\n\n=== DATA MARKET SAAT INI ===\n{snapshot_text}"
    
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            timeout=90
        )
        result = json.loads(resp.choices[0].message.content)
        
        # --- PANGGIL SATPAM DI SINI ---
        if "setup_daily" in result: result["setup_daily"] = validate_setup(result["setup_daily"], "Daily")
        if "setup_session" in result: result["setup_session"] = validate_setup(result["setup_session"], "Session")
            
        return result
    except Exception as e:
        return {"error": f"Nemotron Error: {str(e)}"}

# ==========================================
# 2. FUNGSI ANALISA KHUSUS DEEPSEEK (TETEP PAKE SATPAM)
# ==========================================
def analyze_deepseek(snapshot_text: str, memory_summary: str) -> dict:
    client = OpenAI(
        base_url="https://api.sakelar.web.id/v1", 
        api_key=os.environ.get("SAKELAR_API_KEY", "")
    )
    MODEL = "deepseek-v4.1-flash"
    user_payload = f"{memory_summary}\n\n=== DATA MARKET SAAT INI ===\n{snapshot_text}"
    
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            timeout=90
        )
        result = json.loads(resp.choices[0].message.content)
        
        # --- PANGGIL SATPAM DI SINI ---
        if "setup_daily" in result: result["setup_daily"] = validate_setup(result["setup_daily"], "Daily")
        if "setup_session" in result: result["setup_session"] = validate_setup(result["setup_session"], "Session")
            
        return result
    except Exception as e:
        return {"error": f"DeepSeek Error: {str(e)}"}
