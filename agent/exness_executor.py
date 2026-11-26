import os, time, hmac, hashlib, json, httpx

# Ambil kredensial dari Environment Variables (GitHub Secrets)
EXNESS_API_KEY = os.getenv("EXNESS_API_KEY")
EXNESS_API_SECRET = os.getenv("EXNESS_API_SECRET")
EXNESS_ACCOUNT_ID = os.getenv("EXNESS_ACCOUNT_ID")

# Host dari screenshot dashboard lu
EXNESS_HOST = os.getenv("EXNESS_HOST", "api.exness.com") 

def _send_order_request(payload: dict):
    """Fungsi bantuan buat nembak API Exness + Bikin HMAC Signature"""
    if not all([EXNESS_API_KEY, EXNESS_API_SECRET, EXNESS_ACCOUNT_ID]):
        return {"error": "Exness API credentials kosong di GitHub Secrets."}

    body_str = json.dumps(payload, separators=(',', ':'))
    timestamp = str(int(time.time() * 1000))
    
    # Endpoint berdasarkan referensi backend Exness
    path = "/api/v1/trade/create"
    
    # Signature HMAC (Format: timestamp + POST + path + body)
    message = timestamp + "POST" + path + body_str
    signature = hmac.new(
        EXNESS_API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Headers (Pastikan nama header ini sesuai dengan dokumentasi resmi di dashboard lu)
    headers = {
        "Content-Type": "application/json",
        "EXNESS-API-KEY": EXNESS_API_KEY,
        "EXNESS-API-TIMESTAMP": timestamp,
        "EXNESS-API-SIGNATURE": signature
    }

    try:
        url = f"https://{EXNESS_HOST}{path}"
        resp = httpx.post(url, headers=headers, content=body_str, timeout=15)
        
        # Kalau response bukan 200/201, tangkap pesan errornya
        if resp.status_code not in [200, 201]:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
            
        return {"success": True, "data": resp.json()}
        
    except Exception as e:
        return {"error": f"Request Error: {str(e)}"}


def place_limit_order(symbol: str, action: str, price: float, sl: float, tp: float, volume: float = 0.01):
    """Fungsi buat nembak Limit Order ke Exness API"""
    order_side = "buy" if "BUY" in action.upper() else "sell"
    
    payload = {
        "accountId": EXNESS_ACCOUNT_ID,
        "symbol": symbol.upper(),
        "side": order_side,
        "type": "LIMIT",
        "price": float(price),
        "stopLoss": float(sl),
        "takeProfit": float(tp),
        "volume": float(volume),
        "timeInForce": "GTC" 
    }
    
    return _send_order_request(payload)


def place_market_order(symbol: str, action: str, sl: float, tp: float, volume: float = 0.01):
    """Fungsi buat nembak Market Order (Langsung Eksekusi)"""
    order_side = "buy" if "BUY" in action.upper() else "sell"
    
    payload = {
        "accountId": EXNESS_ACCOUNT_ID,
        "symbol": symbol.upper(),
        "side": order_side,
        "type": "MARKET",
        # "price" dihapus karena market order tembak langsung
        "stopLoss": float(sl),
        "takeProfit": float(tp),
        "volume": float(volume)
    }
    
    return _send_order_request(payload)
