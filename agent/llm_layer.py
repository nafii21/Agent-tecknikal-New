import json, os, base64, re
from openai import OpenAI

client = OpenAI(
    base_url="https://api.sakelar.web.id/v1", 
    api_key=os.environ.get("SAKELAR_API_KEY", "")
)
MODEL = "gpt-5.6-terra" # Pastikan ini model vision

# --- PROMPT H1 (Konteks Utama) ---
PROMPT_H1 = """
Kamu adalah "Institutional Sniper AI".
Tugasmu: Menganalisa GAMBAR CHART H1 dan menentukan status market (WAIT, PREPARE, ENTRY).

ATURAN:
1. Cari Swing High/Low. Apakah ada BOS/CHoCH?
2. Cari Liquidity Sweep (wick panjang).
3. Cari POI (OB/FVG).
4. Cek Trend EMA 20 & 50.

Jika belum ada sweep atau harga di tengah, berikan status "WAIT" dan skenario masa depan.
OUTPUT JSON:
{
  "status": "WAIT|PREPARE|ENTRY",
  "context_reason": "Analisa H1...",
  "setup_type": "Liq Sweep | Counter-Trend | Following-Trend | None",
  "bias": "BULLISH|BEARISH",
  "entry": float, "sl": float, "tp1": float, "tp2": float, "rr": float,
  "trigger": "Syarat konfirmasi"
}
"""

# --- PROMPT M15 (Pencarian Likuiditas) ---
PROMPT_M15 = """
Kamu adalah "LTF Liquidity Hunter". Kita sudah cek H1 dan hasilnya WAIT.
Tugasmu: Turun ke M15. Cari tahu likuiditas mana yang BARU SAJA TERAMBIL (Sweep) di M15.
Setelah sweep terjadi, cari CHoCH (Change of Character) di M15 sebagai konfirmasi reversal.

ATURAN:
1. Jika belum ada sweep likuiditas di M15, status = "WAIT".
2. Jika ada sweep tapi belum ada CHoCH, status = "PREPARE".
3. Jika ada sweep + CHoCH + FVG/OB, status = "ENTRY".

OUTPUT JSON (SAMA SEPERTI H1):
{
  "status": "WAIT|PREPARE|ENTRY",
  "context_reason": "Analisa M15 (Sweep mana yang terambil)...",
  "setup_type": "Liq Sweep",
  "bias": "BULLISH|BEARISH",
  "entry": float, "sl": float, "tp1": float, "tp2": float, "rr": float,
  "trigger": "Syarat konfirmasi"
}
"""

def _call_vision_api(prompt, image_path, text_data):
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Data pendukung:\n{text_data}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            temperature=0.2,
            max_tokens=1500,
            timeout=120
        )
        
        raw_content = resp.choices[0].message.content
        start = raw_content.find('{')
        end = raw_content.rfind('}')
        if start != -1 and end != -1:
            return json.loads(raw_content[start:end+1])
        return {"error": "Format JSON tidak ditemukan."}
    except Exception as e:
        return {"error": f"API Error: {str(e)}"}

def analyze_h1(image_path, text_data):
    return _call_vision_api(PROMPT_H1, image_path, text_data)

def analyze_m15(image_path, text_data):
    return _call_vision_api(PROMPT_M15, image_path, text_data)
