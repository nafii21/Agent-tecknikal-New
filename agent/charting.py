import pandas as pd
import mplfinance as mpf
import os

def generate_chart(df_h1: pd.DataFrame, symbol: str) -> str:
    try:
        # Ambil 100 candle terakhir biar AI bisa liat struktur lebih luas
        df = df_h1.tail(100).copy()
        df = df.set_index('timestamps')
        df.index = pd.to_datetime(df.index)
        
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
        
        # Hitung EMA 20 & 50 buat AI liat trend
        df['EMA20'] = df['Close'].ewm(span=20).mean()
        df['EMA50'] = df['Close'].ewm(span=50).mean()

        # Style Dark Mode (mirip TradingView)
        mc = mpf.make_marketcolors(up='#26a69a', down='#ef5350', edge='inherit', wick='inherit', volume='in')
        s  = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, gridstyle=':')

        apds = [
            mpf.make_addplot(df['EMA20'], color='yellow', width=1),
            mpf.make_addplot(df['EMA50'], color='blue', width=1)
        ]

        filename = f"chart_{symbol}.png"
        title = f"\n{symbol} H1 Structure"
        
        # Gambar (Tanpa Volume biar bersih)
        mpf.plot(
            df, type='candle', style=s, title=title, 
            addplot=apds, volume=False, figratio=(16, 9), figscale=1.2,
            savefig=dict(fname=filename, bbox_inches='tight', dpi=150)
        )
        return filename
    except Exception as e:
        print(f"Error chart: {e}")
        return None
