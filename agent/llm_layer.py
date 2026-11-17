import json, os, base64
from openai import OpenAI

client = OpenAI(
    base_url="https://api.sakelar.web.id/v1", 
    api_key=os.environ.get("SAKELAR_API_KEY", "")
)

# WAJIB pakai model vision. Contoh: Claude Sonnet atau DeepSeek V4
MODEL = "anthropic/claude-5-5-sonnet" 

SYSTEM_PROMPT = """
Kamu adalah "Institutional Sniper AI" dengan keahlian SMC/ICT.
Tugasmu: Menganalisa GAMBAR CHART H1 yang dilampirkan dan menentukan status market (WAIT, PREPARE, ENTRY).

ATURAN VISUAL SMC:
1. Lihat Gambar: Cari Swing High/Low. Apakah ada BOS (tren lanjut) atau CHoCH (reversal)?
2. Cari Liquidity Sweep: Apakah ada ekor panjang (wick) yang nyapu High/Low sebelumnya?
3. Cari POI: Apakah ada Order Block (candle besar terakhir sebelum BOS) atau FVG (celah)?
4. Cek Trend: Lihat garis EMA 20 (kuning) dan 50 (biru). Harga di atas atau di bawah?

ATURAN STATE MACHINE:
1. STATUS "WAIT": Jika harga di tengah jalan, belum ada sweep, dan struktur belum jelas. Berikan skenario lanjutan (misal: "Tunggu harga nyentuh Swing High di X").
2. STATUS "PREPARE": Jika harga sedang mendekati area kunci (OB/FVG/Swing).
3. STATUS "ENTRY": Jika konfirmasi visual jelas (misal: Sweep + CHoCH) dan RR minimal 1:2.

OUTPUT HARUS JSON VALID:
{
  "status": "WAIT|PREPARE|ENTRY",
  "context_reason": "Analisa visual struktur yang terlihat di gambar",
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

def analyze(image_path: str, text_data: str) -> dict:
    try:
        # Konversi gambar ke Base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Berikut data pendukung (Session/SMC):\n{text_data}\n\nTolong analisa gambar chart H1 ini."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=1500,
            timeout=120
        )
        
        raw_content = resp.choices[0].message.content
        if not raw_content or raw_content.strip() == "":
            return {"error": "API ngasih respon kosong. Cek saldo atau nama model Vision."}
            
        return json.loads(raw_content)
    except Exception as e:
        return {"error": f"Vision AI Error: {str(e)}"}
