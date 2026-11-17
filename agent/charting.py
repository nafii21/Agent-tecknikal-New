import pandas as pd
import mplfinance as mpf
import os

def generate_chart(df_h1: pd.DataFrame, symbol: str, sessions: dict) -> str:
    try:
        # Ambil 60 candle terakhir
        df = df_h1.tail(60).copy()
        df = df.set_index('timestamps')
        df.index = pd.to_datetime(df.index)
        
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})

        # Style Dark Mode
        mc = mpf.make_marketcolors(up='#26a69a', down='#ef5350', edge='inherit', wick='inherit', volume='in')
        s  = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)

        # Garis Horizontal buat Session
        hlines = []
        colors = []
        if "Asia" in sessions:
            hlines.append(sessions["Asia"]["high"])
            colors.append('yellow')
            hlines.append(sessions["Asia"]["low"])
            colors.append('yellow')
        
        if "London" in sessions:
            hlines.append(sessions["London"]["high"])
            colors.append('cyan')
            hlines.append(sessions["London"]["low"])
            colors.append('cyan')

        if "New York" in sessions:
            hlines.append(sessions["New York"]["high"])
            colors.append('orange')
            hlines.append(sessions["New York"]["low"])
            colors.append('orange')

        # Render
        filename = f"chart_{symbol}.png"
        title = f"\n{symbol} H1 - Context"
        
        # Gabungin parameter hlines
        plot_kwargs = dict(
            type='candle', style=s, title=title, volume=True,
            figratio=(16, 9), figscale=1.2,
            savefig=dict(fname=filename, bbox_inches='tight', dpi=120)
        )
        
        if hlines:
            plot_kwargs['hlines'] = dict(hlines=hlines, colors=colors, linestyle='--', linewidths=1)
            
        mpf.plot(df, **plot_kwargs)
        return filename
    except Exception as e:
        print(f"Error chart: {e}")
        return None
