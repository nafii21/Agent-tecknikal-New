import json, os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.sakelar.web.id/v1", 
    api_key=os.environ.get("SAKELAR_API_KEY", "")
)
# Pake model yang stabil dulu
MODEL = "deepseek-v4.1-flash" 

SYSTEM_PROMPT = """
Kamu adalah "Institutional Sniper AI" dengan keahlian SMC/ICT.
Tugasmu: Menentukan status market (WAIT, PREPARE, ENTRY) dan memberikan SKENARIO LANJUTAN.

ATURAN STATE MACHINE:
1. STATUS "WAIT": Berikan WAIT jika harga jauh dari Session/Swing, belum ada BOS baru, atau belum ada Sweep.
   -> JIKA STATUS WAIT: Kamu WAJIB menganalisa struktur mentah H1 (Trend EMA & Swing terdekat). 
   -> Berikan "Skenario Masa Depan": Misal "Harga sedang menuju Swing High 27000. Jika terjadi sweep di sana, pantau CHoCH M5 untuk Sell."
2. STATUS "PREPARE": Berikan PREPARE jika harga sedang mendekati (<0.5%) Liquidity/Swing/Session.
3. STATUS "ENTRY": Berikan ENTRY jika Konteks H1 valid + Konfirmasi M5 (FVG/CHoCH) + RR minimal 1:2.

OUTPUT HARUS JSON VALID:
{
  "status": "WAIT|PREPARE|ENTRY",
  "context_reason": "Analisa struktur saat ini & skenario lanjutan (jelaskan kemana harga akan bergerak)",
  "setup_type": "Liq Sweep | Counter-Trend | Following-Trend | None",
  "bias": "BULLISH|BEARISH",
  "entry": float (isi 0 jika WAIT/PREPARE),
  "sl": float,
  "tp1": float,
  "tp2": float,
  "rr": float,
  "trigger": "Syarat konfirmasi (misal: 'Tunggu sweep di 27000 lalu CHoCH M5')"
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
            temperature=0.3, # Naikin dikit biar AI lebih kreatif nyusun skenario
            response_format={"type": "json_object"},
            max_tokens=1500,
            timeout=90
        )
        
        raw_content = resp.choices[0].message.content
        if not raw_content or raw_content.strip() == "":
            return {"error": "API ngasih respon kosong. Cek saldo Sakelar."}
            
        return json.loads(raw_content)
    except Exception as e:
        return {"error": f"AI Error: {str(e)}"}
