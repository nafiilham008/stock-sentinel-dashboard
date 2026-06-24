import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

def get_stock_history(ticker, period="3mo"):
    """
    Fetches historical data for a ticker.
    """
    if not ticker.endswith(".JK"):
        ticker = f"{ticker}.JK"
        
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False)
        return df
    except Exception as e:
        print(f"Error fetching history for {ticker}: {e}")
        return pd.DataFrame()

def create_price_chart(ticker, period="3mo"):
    """
    Creates a Plotly CandleStick chart for the given ticker.
    """
    df = get_stock_history(ticker, period)
    
    if df.empty:
        return None
        
    # Flatten MultiIndex columns if necessary (yfinance update quirk)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Calculate Moving Averages
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()

    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="Price"
    ))
    
    # Add MA5 (BPJS/Short-term baseline)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MA5'],
        mode='lines',
        line=dict(color='orange', width=1.5),
        name='MA5 (1 Minggu)'
    ))
    
    # Add MA20 (Swing baseline)
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['MA20'],
        mode='lines',
        line=dict(color='blue', width=1.5),
        name='MA20 (1 Bulan)'
    ))
    
    # Add Buy Signals (Momentum BPJS: Cross above MA5 strongly)
    buy_signals = df[(df['Close'] > df['MA5']) & (df['Close'].shift(1) <= df['MA5'].shift(1)) & (df['Close'] > df['Open'])]
    if not buy_signals.empty:
        fig.add_trace(go.Scatter(
            x=buy_signals.index,
            y=buy_signals['Low'] * 0.98, # Slightly below the candle
            mode='markers',
            marker=dict(symbol='triangle-up', size=14, color='lime', line=dict(width=1, color='darkgreen')),
            name='Momentum Buy (BPJS Radar)'
        ))
    
    fig.update_layout(
        title=f"Price History: {ticker} ({period})",
        yaxis_title="Price (IDR)",
        xaxis_title="Date",
        template="plotly_dark", # Matches Streamlit dark mode nicely
        height=400,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_rangeslider_visible=False
    )
    
    return fig
