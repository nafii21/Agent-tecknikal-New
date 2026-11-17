import json, os, base64, re
from openai import OpenAI

client = OpenAI(
    base_url="https://api.sakelar.web.id/v1", 
    api_key=os.environ.get("SAKELAR_API_KEY", "")
)

# PASTIKAN MODEL INI SUPPORT GAMBAR (VISION). 
# Kalau ragu, coba "claude-3-5-sonnet" atau "gpt-4o".
MODEL = "gpt-5.6-terra" 

SYSTEM_PROMPT = """
Kamu adalah "Institutional Sniper AI" dengan keahlian SMC/ICT.
Tugasmu: Menganalisa GAMBAR CHART H1 yang dilampirkan dan menentukan status market (WAIT, PREPARE, ENTRY).

ATURAN VISUAL SMC:
1. Lihat Gambar: Cari Swing High/Low. Apakah ada BOS (tren lanjut) atau CHoCH (reversal)?
2. Cari Liquidity Sweep: Apakah ada ekor panjang (wick) yang nyapu High/Low sebelumnya?
3. Cari POI: Apakah ada Order Block (candle besar terakhir sebelum BOS) atau FVG (celah)?
4. Cek Trend: Lihat garis EMA 20 (kuning) dan 50 (biru). Harga di atas atau di bawah?

ATURAN STATE MACHINE:
1. STATUS "WAIT": Jika harga di tengah jalan, belum ada sweep, dan struktur belum jelas. Berikan skenario lanjutan.
2. STATUS "PREPARE": Jika harga sedang mendekati area kunci (OB/FVG/Swing).
3. STATUS "ENTRY": Jika konfirmasi visual jelas dan RR minimal 1:2.

OUTPUT HARUS JSON VALID (TANPA MARKDOWN, TANPA TEKS LAIN):
{
  "status": "WAIT|PREPARE|ENTRY",
  "context_reason": "Analisa visual struktur yang terlihat di gambar",
  "setup_type": "Liq Sweep | Counter-Trend | Following-Trend | None",
  "bias": "BULLISH|BEARISH",
  "entry": float,
  "sl": float,
  "tp1": float,
  "tp2": float,
  "rr": float,
  "trigger": "Syarat konfirmasi"
}
"""

def analyze(image_path: str, text_data: str) -> dict:
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Berikut data pendukung:\n{text_data}\n\nAnalisa gambar chart H1 ini."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            temperature=0.2,
            # response_format={"type": "json_object"}, <--- GW HAPUS INI
            max_tokens=1500,
            timeout=120
        )
        
        raw_content = resp.choices[0].message.content
        if not raw_content or raw_content.strip() == "":
            return {"error": "API ngasih respon kosong."}
            
        # --- SATPAM EKSTRAKSI JSON ---
        # Kadang AI nambahin teks kayak "Ini hasilnya: { ... }"
        # Kita cari kurung kurawal pertama dan terakhir
        start = raw_content.find('{')
        end = raw_content.rfind('}')
        
        if start != -1 and end != -1:
            json_str = raw_content[start:end+1]
            return json.loads(json_str)
        else:
            return {"error": f"AI gagal ngasih JSON. Jawaban asli: {raw_content[:100]}..."}

    except Exception as e:
        return {"error": f"Vision AI Error: {str(e)}"}
