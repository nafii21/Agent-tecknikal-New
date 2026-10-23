import json, os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", "")
)

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"

SYSTEM_PROMPT = """
Kamu adalah "Institutional Fund Manager". Tugasmu menganalisa data Snapshot Market yang sangat lengkap (Fundamental Makro, Multi-Timeframe, Pivot, Fibo).
Buatlah rencana trading (Plan A dan Plan B) yang presisi.

ATURAN:
1. Tentukan Bias (Bullish/Bearish) dari D1 dan Fundamental.
2. Cari Sweet Spot Entry (di area Fibo 50%, Pivot, atau EMA).
3. Wajib kasih 2 Plan: Plan A (Searah Tren) dan Plan B (Cadangan).
4. RR wajib minimal 1:2.
5. Berikan "Narrative" (cerita kondisi market saat ini berdasarkan DXY, Yield, Oil dan teknikal).

OUTPUT HARUS JSON VALID:
{
  "bias": "BULLISH|BEARISH",
  "narrative": "Penjelasan detail kondisi market hari ini...",
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
