import os, time, hmac, hashlib, json, httpx

EXNESS_API_KEY = os.getenv("EXNESS_API_KEY")
EXNESS_API_SECRET = os.getenv("EXNESS_API_SECRET")
EXNESS_ACCOUNT_ID = os.getenv("EXNESS_ACCOUNT_ID")

BASE_URL = "https://api.exness.com" 

def _send_order_request(payload: dict):
    """Fungsi bantuan buat nembak API Exness + Bikin HMAC Signature"""
    if not all([EXNESS_API_KEY, EXNESS_API_SECRET, EXNESS_ACCOUNT_ID]):
        return {"error": "Exness API credentials kosong di GitHub Secrets."}

    body_str = json.dumps(payload, separators=(',', ':'))
    timestamp = str(int(time.time() * 1000))
    
    # 🔥 FIX 1: Endpoint yang bener buat create order
    path = "/api/v1/trade/create" 

    # Format signature: timestamp + method + path + body
    message = timestamp + "POST" + path + body_str
    signature = hmac.new(
        EXNESS_API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "EXNESS-API-KEY": EXNESS_API_KEY,
        "EXNESS-API-SIGNATURE": signature,
        "EXNESS-API-TIMESTAMP": timestamp,
        "Content-Type": "application/json"
    }

    try:
        url = f"{BASE_URL}{path}"
        resp = httpx.post(url, headers=headers, content=body_str, timeout=15)
        
        # 🔥 FIX 2: Cek status code dulu sebelum parsing JSON
        if resp.status_code not in [200, 201]:
            # Kalau bukan 200/201, balikin text aslinya biar kita tau error dari Exness
            return {"error": f"Exness HTTP {resp.status_code}: {resp.text[:200]}"}
            
        # Coba parsing JSON
        try:
            resp_json = resp.json()
        except json.JSONDecodeError:
            # Kalau gagal parsing JSON (misal dapet HTML), balikin potongan text-nya
            return {"error": f"Respon bukan JSON (kemungkinan URL salah). Isi: {resp.text[:100]}"}
        
        # Cek apakah Exness ngasih error di dalam JSON-nya
        if "error" in resp_json:
            return {"error": f"Exness API Error: {resp_json}"}
            
        return {"success": True, "order_id": resp_json.get("orderId", "Unknown"), "data": resp_json}
            
    except Exception as e:
        return {"error": f"Request Error: {str(e)}"}


def place_limit_order(symbol: str, action: str, price: float, sl: float, tp: float, volume: float = 0.01):
    """Fungsi buat nembak Limit Order ke Exness API"""
    order_side = "buy" if "BUY" in action.upper() else "sell"
    
    payload = {
        "accountId": EXNESS_ACCOUNT_ID,
        "symbol": symbol.upper(),
        "type": order_side, # Exness biasanya pakai 'buy'/'sell', bukan 'side'
        "orderType": "Limit",
        "price": float(price),
        "stopLoss": float(sl),
        "takeProfit": float(tp),
        "volume": float(volume),
        "timeInForce": "GTC" 
    }
    
    return _send_order_request(payload)


def place_market_order(symbol: str, action: str, sl: float, tp: float, volume: float = 0.01):
    """🔥 FUNGSI BARU: Market Order dengan parameter yang benar 🔥"""
    order_side = "buy" if "BUY" in action.upper() else "sell"
    
    payload = {
        "accountId": EXNESS_ACCOUNT_ID,
        "symbol": symbol.upper(),
        "type": order_side, 
        "orderType": "Market", # Pake 'orderType' biar lebih jelas
        "stopLoss": float(sl),
        "takeProfit": float(tp),
        "volume": float(volume),
        "timeInForce": "IOC" # 🔥 FIX 3: Market order wajib IOC
    }
    
    return _send_order_request(payload)
