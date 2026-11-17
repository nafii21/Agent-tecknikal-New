import json, os, base64
from openai import OpenAI

client = OpenAI(
    base_url="https://api.sakelar.web.id/v1", 
    api_key=os.environ.get("SAKELAR_API_KEY", "")
)
MODEL = "gpt-5.6-terra" 

PROMPT_H1 = """
Kamu adalah "Institutional Sniper AI".
Tugasmu: Menganalisa GAMBAR CHART H1 dan menentukan status market (WAIT, PREPARE, ENTRY).
ATURAN: Cari BOS/CHoCH, Sweep, POI, dan Trend.
OUTPUT JSON: {"status": "WAIT|PREPARE|ENTRY", "context_reason": "...", "setup_type": "...", "bias": "BULLISH|BEARISH", "entry": float, "sl": float, "tp1": float, "tp2": float, "rr": float, "trigger": "..."}
"""

PROMPT_M15 = """
Kamu adalah "LTF Liquidity Hunter". H1 sedang WAIT.
Tugasmu: Analisa GAMBAR CHART M15. Cari likuiditas yang BARU SAJA TERAMBIL (Sweep) dan cari CHoCH sebagai konfirmasi reversal.
OUTPUT JSON: {"status": "WAIT|PREPARE|ENTRY", "context_reason": "...", "setup_type": "...", "bias": "BULLISH|BEARISH", "entry": float, "sl": float, "tp1": float, "tp2": float, "rr": float, "trigger": "..."}
"""

PROMPT_M1 = """
Kamu adalah "M1 Sniper Trigger". M15 sudah memberikan arah setup (PREPARE/ENTRY).
Tugasmu: Analisa GAMBAR CHART M1. Cari konfirmasi paling presisi: 
1. Apakah ada CHoCH di M1?
2. Apakah ada FVG kecil di M1 sebagai area retest?
3. Apakah ada candle rejection (pinbar/engulfing) di area tersebut?

Berikan Entry paling akurat (Sniper) berdasarkan konfirmasi M1, dengan SL di balik struktur M1, dan RR minimal 1:2.
OUTPUT JSON: {"status": "WAIT|PREPARE|ENTRY", "context_reason": "...", "setup_type": "...", "bias": "BULLISH|BEARISH", "entry": float, "sl": float, "tp1": float, "tp2": float, "rr": float, "trigger": "..."}
"""

def _call_vision_api(prompt, image_path, text_data):
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": f"Data pendukung:\n{text_data}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]}
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

def analyze_h1(image_path, text_data): return _call_vision_api(PROMPT_H1, image_path, text_data)
def analyze_m15(image_path, text_data): return _call_vision_api(PROMPT_M15, image_path, text_data)
def analyze_m1(image_path, text_data): return _call_vision_api(PROMPT_M1, image_path, text_data)
