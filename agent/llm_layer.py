import json, os
from openai import OpenAI

# --- PINDAH KE SAKELAR ---
client = OpenAI(
    base_url="https://api.sakelar.web.id/v1", 
    api_key=os.environ.get("SAKELAR_API_KEY", "")
)

# GANTI DENGAN NAMA MODEL YANG LO PILIH DI SAKELAR
MODEL = "gpt-4o" 

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
- Berikan "dynamic_invalidation": Kapan setup ini Batal sebelum kena Entry (misal: "Batal jika harga sudah turun melewati 4095 sebelum order terisi").

OUTPUT HARUS JSON VALID:
{
  "bias": "BULLISH|BEARISH",
  "session_analysis": "Penjelasan kondisi sesi...",
  "narrative": "Penjelasan detail (Fundamental + Teknikal + Swing/ATR)...",
  "key_levels": "Level kunci (Pivot, Fibo 61.8%, Swing High/Low) dalam teks.",
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
    "trigger_entry": "Syarat momentum M15...",
    "dynamic_invalidation": "Syarat batal..."
  }
}
"""

def analyze(snapshot_text: str, memory_summary: str) -> dict:
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
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"error": f"LLM Error: {str(e)}"}
