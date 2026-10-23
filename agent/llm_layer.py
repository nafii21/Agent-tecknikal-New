import json, os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", "")
)

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

SYSTEM_PROMPT = """
Kamu adalah "Institutional Fund Manager". Tugasmu menganalisa data Snapshot Market.
Data yang diberikan berisi: Fundamental Makro (DXY, Yield), Berita Real-time (Web Search), Multi-Timeframe, Pivot, Fibo.

ATURAN ANALISIS:
1. BACA BAGIAN "BERITA FUNDAMENTAL TERBARU". Ini adalah kondisi real-time hari ini. (Misal: Jika berita bilang The Fed mau naikin suku bunga, maka bias bearish untuk Gold).
2. Tentukan Bias Utama (Bullish/Bearish) dari gabungan Berita + D1.
3. Cari Sweet Spot Entry (Fibo 50%, Pivot, EMA) berdasarkan Price Action.
4. Sesuaikan rencana dengan Sesi (Asia = ranging, London = fakeout, NY = volatile).
5. Wajib kasih 2 Plan: Plan A (Searah Tren) dan Plan B (Cadangan).
6. RR wajib minimal 1:2.

OUTPUT HARUS JSON VALID:
{
  "bias": "BULLISH|BEARISH",
  "session_analysis": "Penjelasan kondisi market di sesi ini...",
  "narrative": "Penjelasan detail (Gabungan berita fundamental dan teknikal)...",
  "plan_a": {
    "action": "BUY_LIMIT|SELL_LIMIT|WAIT",
    "entry": float,
    "sl": float,
    "tp1": float,
    "tp2": float,
    "invalidation": "Plan A batal jika..."
  },
  "plan_b": {
    "action": "BUY_LIMIT|SELL_LIMIT|WAIT",
    "entry": float,
    "sl": float,
    "tp1": float,
    "tp2": float,
    "invalidation": "Plan B batal jika..."
  }
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
        )
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"error": f"LLM Error: {str(e)}"}
