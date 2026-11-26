import os, time, hmac, hashlib, json, httpx

EXNESS_API_KEY = os.getenv("EXNESS_API_KEY")
EXNESS_API_SECRET = os.getenv("EXNESS_API_SECRET")
EXNESS_ACCOUNT_ID = os.getenv("EXNESS_ACCOUNT_ID")
# ⚠️ PENTING: Ganti dengan host dari dashboard API Exness lu (contoh: ap-4decef67.exness.com)
EXNESS_HOST = os.getenv("EXNESS_HOST", "ap-4decef67.exness.com") 

def _generate_signature(timestamp, method, path, body_str, idempotency_key):
    """Bikin signature HMAC sesuai dokumentasi Exness API"""
    # Format signature: timestamp + method + path + body + idempotency_key
    message = f"{timestamp}{method}{path}{body_str}{idempotency_key}"
    return hmac.new(
        EXNESS_API_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def _send_order_request(payload: dict, idempotency_key: str):
    """Fungsi bantuan buat nembak API Exness"""
    if not all([EXNESS_API_KEY, EXNESS_API_SECRET, EXNESS_ACCOUNT_ID]):
        return {"error": "Exness API credentials kosong di GitHub Secrets."}

    body_str = json.dumps(payload, separators=(',', ':'))
    timestamp = str(int(time.time() * 1000))
    
    # 🔥 FIX: Path yang bener buat buka posisi
    path = f"/v1/trading/accounts/{EXNESS_ACCOUNT_ID}/positions"
    signature = _generate_signature(timestamp, "POST", path, body_str, idempotency_key)

    headers = {
        "Content-Type": "application/json",
        "EXN-API-KEY": EXNESS_API_KEY,
        "EXN-TIMESTAMP": timestamp,
        "EXN-SIGN": signature,
        "EXN-SIGN-VERSION": "1",
        "EXN-IDEMPOTENCY-KEY": idempotency_key
    }

    try:
        url = f"https://{EXNESS_HOST}{path}"
        resp = httpx.post(url, headers=headers, content=body_str, timeout=15)
        
        if resp.status_code not in [200, 201, 202]:
            return {"error": f"Exness HTTP {resp.status_code}: {resp.text[:300]}"}
            
        resp_json = resp.json()
        
        # Exness ngasih ACK dulu, bukan final status
        if "operation_id" in resp_json:
            return {"success": True, "operation_id": resp_json["operation_id"], "status": "ACK_RECEIVED"}
            
        return {"success": True, "data": resp_json}
            
    except Exception as e:
        return {"error": f"Request Error: {str(e)}"}

def place_market_order(symbol: str, action: str, sl: float, tp: float, volume: float = 0.01):
    """🔥 Market Order sesuai dokumentasi Exness API 🔥"""
    order_side = "buy" if "BUY" in action.upper() else "sell"
    
    # 📌 Dokumentasi Exness: body cuma butuh instrument, side, volume, SL, TP
    payload = {
        "instrument": symbol.upper(),
        "side": order_side,
        "volume": str(volume), # Exness minta string buat volume
        "stopLoss": str(sl),
        "takeProfit": str(tp)
    }
    
    idempotency_key = f"order-{int(time.time())}-{order_side}"
    return _send_order_request(payload, idempotency_key)

# Fungsi place_limit_order biarkan dulu, atau hapus jika tidak dipakai
