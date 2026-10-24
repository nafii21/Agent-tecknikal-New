import feedparser

def get_market_news(symbol: str) -> str:
    # Mapping ticker buat RSS Yahoo Finance
    rss_tickers = {
        "XAUUSD": "GC=F",
        "BTCUSD": "BTC-USD",
        "NASDAQ": "NQ=F",
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X"
    }
    
    ticker = rss_tickers.get(symbol.upper(), "GC=F")
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    
    try:
        # Ambil berita via RSS (Super Cepat & Anti-Blokir)
        feed = feedparser.parse(url)
        
        if not feed.entries:
            return "===== BERITA FUNDAMENTAL TERBARU =====\nTidak ada berita terbaru yang ditemukan.\n"
            
        news_text = "===== BERITA FUNDAMENTAL TERBARU (YAHOO FINANCE RSS) =====\n"
        # Ambil 3 berita teratas
        for i, entry in enumerate(feed.entries[:3]):
            news_text += f"{i+1}. {entry.title}\n"
            
        return news_text
    except Exception as e:
        return f"===== BERITA FUNDAMENTAL TERBARU =====\nGagal mengambil berita: {str(e)}\n"
