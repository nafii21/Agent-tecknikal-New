import json, os
from openai import OpenAI

# --- KITA PINDAH KE SAKELAR ---
client = OpenAI(
    base_url="https://api.sakelar.web.id/v1", 
    api_key=os.environ.get("SAKELAR_API_KEY", "")
)

# Pilih model: "kimi-k3.1-pro" atau "deepseek-v4.1-flash"
MODEL = "anthropic/claude-sonnet-5.5" 

SYSTEM_PROMPT = """
Kamu adalah "Institutional Sniper AI" dengan keahlian SMC/ICT.
Tugasmu: Menentukan status market (WAIT, PREPARE, atau ENTRY) berdasarkan data H1 dan M5.

ATURAN STATE MACHINE:
1. STATUS "WAIT": Berikan WAIT jika harga jauh dari Session High/Low, atau belum ada BOS/CHoCH baru di H1, atau belum ada Liquidity Sweep. (Belum ada konteks).
2. STATUS "PREPARE": Berikan PREPARE jika harga sedang MENDEKATI (jarak < 0.5%) area Liquidity Sweep, Session High/Low, atau OB/FVG H1 yang valid. 
3. STATUS "ENTRY": Berikan ENTRY jika:
   - Konteks H1 valid (searah tren atau counter-trend di zona kunci).
   - Ada konfirmasi di M5 (CHoCH/BOS di M5, atau FVG M5 yang fresh).
   - Setup searah atau melawan H1 dengan alasan jelas.
   - RR minimal 1:2.

SETUP ENTRY YANG DIIZINKAN:
- Liq Sweep Reversal (Sapu High/Low lalu berbalik).
- Counter-Trend (Melawan tren H1 jika ada FVG M5 dan sweep).
- Following-Trend (Mengikuti BOS H1, entry di FVG/OB H1).

OUTPUT HARUS JSON VALID:
{
  "status": "WAIT|PREPARE|ENTRY",
  "context_reason": "Alasan kenapa milih status ini (cek jarak ke session/liq)",
  "setup_type": "Liq Sweep | Counter-Trend | Following-Trend | None",
  "bias": "BULLISH|BEARISH",
  "entry": float (isi 0 jika WAIT/PREPARE),
  "sl": float,
  "tp1": float,
  "tp2": float,
  "rr": float,
  "trigger": "Syarat konfirmasi (misal: 'Tunggu candle M5 close di atas X')"
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
            response_format={"type": "json_object"},
            max_tokens=1500, # <--- INI KUNCINYA BIAR GA ERROR 402
            timeout=120 # Kimi agak lambat, kasih waktu 2 menit
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"error": f"Kimi Error: {str(e)}"}
