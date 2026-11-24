import os, time, hmac, hashlib, json, httpx

EXNESS_API_KEY = os.getenv("EXNESS_API_KEY")
EXNESS_API_SECRET = os.getenv("EXNESS_API_SECRET")
EXNESS_ACCOUNT_ID = os.getenv("EXNESS_ACCOUNT_ID")

# Base URL standar Exness API (bisa berubah sesuai dokumentasi terbaru)
BASE_URL = "https://api.exness.com" 

def place_limit_order(symbol: str, action: str, price: float, sl: float, tp: float, volume: float = 0.01):
    """Fungsi buat nembak Limit Order ke Exness API"""
    if not all([EXNESS_API_KEY, EXNESS_API_SECRET, EXNESS_ACCOUNT_ID]):
        return {"error": "Exness API credentials kosong di GitHub Secrets."}

    # 1. Tentukan tipe order
    order_side = "BUY" if "BUY" in action.upper() else "SELL"
    
    # 2. Format Payload (Sesuaikan dengan dokumentasi Exness API)
    payload = {
        "accountId": EXNESS_ACCOUNT_ID,
        "symbol": symbol.upper(),
        "side": order_side,
        "type": "LIMIT",
        "price": float(price),
        "stopLoss": float(sl),
        "takeProfit": float(tp),
        "volume": float(volume),
        "timeInForce": "GTC" # Good Till Cancelled
    }
    
    body_str = json.dumps(payload, separators=(',', ':'))
    timestamp = str(int(time.time() * 1000)) # Exness biasanya minta milidetik
    path = "/api/v1/trading/orders" # Path standar REST trading

    # 3. Bikin HMAC Signature (Wajib untuk Exness API)
    # Format signature: timestamp + method + path + body
    message = timestamp + "POST" + path + body_str
    signature = hmac.new(
        EXNESS_API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # 4. Headers
    headers = {
        "EXNESS-API-KEY": EXNESS_API_KEY,
        "EXNESS-API-SIGNATURE": signature,
        "EXNESS-API-TIMESTAMP": timestamp,
        "Content-Type": "application/json"
    }

    # 5. Tembak API
    try:
        url = f"{BASE_URL}{path}"
        resp = httpx.post(url, headers=headers, content=body_str, timeout=15)
        resp_json = resp.json()
        
        if resp.status_code in [200, 201]:
            return {"success": True, "order_id": resp_json.get("orderId", "Unknown"), "data": resp_json}
        else:
            return {"error": f"Exness Error {resp.status_code}: {resp_json}"}
            
    except Exception as e:
        return {"error": f"Request Error: {str(e)}"}
