import os, httpx, json

# URL tunnel dari Cloudflare/Ngrok (tanpa /mcp di akhir)
MIKA_MCP_URL = os.getenv("MIKA_MCP_URL", "https://random-name.trycloudflare.com/mcp")
MIKA_TOKEN = os.getenv("MIKA_TOKEN", "token_rahasia_dari_mika")

def send_task_to_mika(task_description: str):
    """
    Mengirim perintah ke MIKA via MCP.
    task_description: string instruksi natural language untuk MIKA.
    Contoh: "Buka MT5, pasang BUY LIMIT XAUUSD di 2350, SL 2340, TP 2370"
    """
    headers = {
        "Authorization": f"Bearer {MIKA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Payload standar MCP untuk mengirim prompt/task
    payload = {
        "jsonrpc": "2.0",
        "method": "mcp/task",  # Atau method yang sesuai dokumentasi MIKA
        "params": {
            "prompt": task_description
        },
        "id": 1
    }
    
    try:
        response = httpx.post(MIKA_MCP_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        print(f"✅ Perintah terkirim ke MIKA: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Gagal kirim ke MIKA: {e}")
        return False
