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
    
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name=ticker
    )])
    
    fig.update_layout(
        title=f"Price History: {ticker} ({period})",
        yaxis_title="Price (IDR)",
        xaxis_title="Date",
        template="plotly_dark", # Matches Streamlit dark mode nicely
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig
