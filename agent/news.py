from duckduckgo_search import DDGS

def get_market_news(symbol: str) -> str:
    # Bikin keyword pencarian berdasarkan pair
    keywords = "Gold price news today" if symbol == "XAUUSD" else f"{symbol} price news today"
    
    try:
        # Ambil 3 berita teratas dari internet
        results = DDGS().text(keywords, max_results=3)
        
        if not results:
            return "Tidak ada berita terbaru yang ditemukan."
            
        news_text = "===== BERITA FUNDAMENTAL TERBARU (WEB SEARCH) =====\n"
        for i, res in enumerate(results):
            news_text += f"{i+1}. {res['title']}\n"
            news_text += f"   Sumber: {res['href']}\n"
            # Ambil ringkasan beritanya (body)
            news_text += f"   Ringkasan: {res['body']}\n\n"
            
        return news_text
    except Exception as e:
        return f"Gagal mengambil berita: {str(e)}"
