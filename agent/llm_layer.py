import json, os, re
from openai import OpenAI

# --- KITA PINDAH KE SAKELAR ---
client = OpenAI(
    base_url="https://api.sakelar.web.id/v1", 
    api_key=os.environ.get("SAKELAR_API_KEY", "")
)

# Pastikan nama model ini PERSIS sama kayak yang ada di dashboard Sakelar.
# Contoh format yang biasanya bener: "anthropic/claude-3-5-sonnet"
MODEL = "anthropic/claude-3-5-sonnet" 

SYSTEM_PROMPT = """
Kamu adalah "Institutional Sniper AI" dengan keahlian SMC/ICT.
Tugasmu: Menentukan status market (WAIT, PREPARE, atau ENTRY) berdasarkan data H1 dan M5.

ATURAN STATE MACHINE:
1. STATUS "WAIT": Berikan WAIT jika harga jauh dari Session High/Low, atau belum ada BOS/CHoCH baru di H1, atau belum ada Liquidity Sweep.
2. STATUS "PREPARE": Berikan PREPARE jika harga sedang MENDEKATI (jarak < 0.5%) area Liquidity Sweep, Session High/Low, atau OB/FVG H1 yang valid. 
3. STATUS "ENTRY": Berikan ENTRY jika:
   - Konteks H1 valid.
   - Ada konfirmasi di M5.
   - RR minimal 1:2.

HANYA BALAS DENGAN JSON VALID. TANPA TEKS LAIN.
{
  "status": "WAIT|PREPARE|ENTRY",
  "context_reason": "Alasan kenapa milih status ini",
  "setup_type": "Liq Sweep | Counter-Trend | Following-Trend | None",
  "bias": "BULLISH|BEARISH",
  "entry": float (isi 0 jika WAIT/PREPARE),
  "sl": float,
  "tp1": float,
  "tp2": float,
  "rr": float,
  "trigger": "Syarat konfirmasi"
}
"""

def analyze(snapshot_text: str) -> dict:
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": snapshot_text},
            ],
            temperature=0.2,
            # response_format={"type": "json_object"}, <--- GW MATIIN DULU KARENA KADANG BIKIN PROXY ERROR
            max_tokens=1500, 
            timeout=120 
        )
        
        raw_content = resp.choices[0].message.content
        
        # --- SATPAM JSON BARU ---
        if not raw_content or raw_content.strip() == "":
            return {"error": "API Sakelar ngasih respon KOSONG. Cek saldo lo, atau cek nama model Claude di dashboard Sakelar."}
            
        # Kadang Claude nambahin teks ```json di awal/akhir, kita bersihin
        clean_content = raw_content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(clean_content)
        except json.JSONDecodeError:
            return {"error": f"Format JSON rusak. Isi respon API: {raw_content[:100]}..."}
            
    except Exception as e:
        return {"error": f"Claude API Error: {str(e)}"}
