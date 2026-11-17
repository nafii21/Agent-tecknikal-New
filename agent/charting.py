import pandas as pd
import mplfinance as mpf
import os

def generate_chart(df: pd.DataFrame, symbol: str, timeframe: str) -> str:
    try:
        # --- ZOOM IN UNTUK M1 (30 candle terakhir) ---
        # H1 dan M15 pake 80 candle biar keliatan struktur besarnya
        limit = 30 if timeframe == "M1" else 80
        df = df.tail(limit).copy()
        
        df = df.set_index('timestamps')
        df.index = pd.to_datetime(df.index)
        
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
        
        # Cuma pake EMA20 biar chart M1 nggak terlalu rame
        df['EMA20'] = df['Close'].ewm(span=20).mean()

        mc = mpf.make_marketcolors(up='#26a69a', down='#ef5350', edge='inherit', wick='inherit', volume='in')
        s  = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, gridstyle=':')

        apds = [
            mpf.make_addplot(df['EMA20'], color='yellow', width=1.5)
        ]

        filename = f"chart_{symbol}_{timeframe}.png"
        title = f"\n{symbol} {timeframe} Structure"
        
        # figscale=1.5 bikin gambar lebih gede dan jelas
        mpf.plot(
            df, type='candle', style=s, title=title, 
            addplot=apds, volume=False, figratio=(16, 9), figscale=1.5,
            savefig=dict(fname=filename, bbox_inches='tight', dpi=150)
        )
        return filename
    except Exception as e:
        print(f"Error chart: {e}")
        return None
