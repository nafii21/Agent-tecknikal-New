import os, httpx, json

# Otomatis baca dari GitHub Secrets
MIKA_URL = os.getenv("MIKA_MCP_URL", "")
MIKA_TOKEN = os.getenv("MIKA_TOKEN", "")

def send_task_to_mika(task_description: str):
    if not MIKA_URL:
        print("⚠️ MIKA_MCP_URL belum diset di GitHub Secrets!")
        return False
        
    headers = {
        "Authorization": f"Bearer {MIKA_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": "mcp/task",
        "params": {
            "prompt": task_description
        },
        "id": 1
    }
    
    try:
        # Kirim request ke URL Cloudflare Tunnel
        response = httpx.post(MIKA_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        print(f"✅ Perintah sukses terkirim ke MIKA: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Gagal kirim ke MIKA: {e}")
        return False
