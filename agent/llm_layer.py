import json, os, base64
from openai import OpenAI

client = OpenAI(
    base_url="https://api.sakelar.web.id/v1", 
    api_key=os.environ.get("SAKELAR_API_KEY", "")
)
MODEL = "gpt-5.6-terra" # Pastikan model ini support Vision (baca gambar)

# --- PROMPT H1 (Konteks Utama) ---
PROMPT_H1 = """
Kamu adalah "Institutional Sniper AI".
Tugasmu: Menganalisa GAMBAR CHART H1 dan menentukan status market (WAIT, PREPARE, ENTRY).
ATURAN:
1. Cari BOS/CHoCH.
2. Cari Liquidity Sweep.
3. Cari POI (OB/FVG).
4. Cek Trend EMA 20 & 50.
Jika H1 belum ada sweep atau harga di tengah, berikan status "WAIT".
OUTPUT JSON: {"status": "WAIT|PREPARE|ENTRY", "context_reason": "...", "setup_type": "...", "bias": "BULLISH|BEARISH", "entry": float, "sl": float, "tp1": float, "tp2": float, "rr": float, "trigger": "..."}
"""

# --- PROMPT M15 (Pencarian Likuiditas) ---
PROMPT_M15 = """
Kamu adalah "M15 Liquidity Hunter". H1 memberikan status WAIT.
Tugasmu HANYA SATU: Cari tahu apakah ada likuiditas yang BARU SAJA TERAMBIL (Sweep) di M15, atau apakah harga sedang mendekati POI (OB/FVG) di M15.
JANGAN menunggu CHoCH di M15! Trigger entry akan dicari di M1.
Jika Sweep terdeteksi atau harga menyentuh POI, berikan status "PREPARE".
Jika tidak ada sweep/POI yang dekat, berikan status "WAIT".
OUTPUT JSON: {"status": "WAIT|PREPARE", "context_reason": "Sebutkan sweep mana yang terambil atau POI mana yang didekati", "setup_type": "Liq Sweep", "bias": "BULLISH|BEARISH", "entry": 0, "sl": 0, "tp1": 0, "tp2": 0, "rr": 0, "trigger": "Turun ke M1"}
"""

# --- PROMPT M1 (Sniper Trigger - Lebih Longgar) ---
PROMPT_M1 = """
Kamu adalah "M1 Sniper Trigger". M15 sudah memberikan status PREPARE (ada Sweep/POI).
Tugasmu: Analisa GAMBAR CHART M1 (hanya 30 candle terakhir, zoom in).

KARENA KITA SUDAH DI AREA KUNCI (Sweep/POI), KONFIRMASI TIDAK HARUS SEMPURNA:
1. Cari candle rejection (Pinbar / Engulfing) di area tersebut.
2. ATAU cari iFVG (Inverse FVG) kecil.
3. ATAU cari CHoCH kecil (perubahan arah minor).
JIKA SALAH SATU SAJA TERLIHAT (meskipun kecil), LANGSUNG BERIKAN STATUS "ENTRY".

Berikan Entry Sniper, SL di balik struktur M1 (misal di bawah wick), dan RR minimal 1:2.
Jika benar-benar tidak ada tanda-tanda pembalikan sama sekali (harga jalan lurus), barulah berikan status "WAIT".
OUTPUT JSON: {"status": "WAIT|ENTRY", "context_reason": "...", "setup_type": "...", "bias": "BULLISH|BEARISH", "entry": float, "sl": float, "tp1": float, "tp2": float, "rr": float, "trigger": "..."}
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
