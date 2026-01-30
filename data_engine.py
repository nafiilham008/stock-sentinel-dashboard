import yfinance as yf
import pandas as pd

def get_ticker_data(ticker, period="1mo", interval="1d"):
    """
    Fetches historical data for a single ticker.
    Ensures ticker has .JK suffix for IDX stocks if not present.
    """
    if not ticker.endswith(".JK"):
        ticker = f"{ticker}.JK"
    
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period, interval=interval)
    return hist

def get_current_price(ticker):
    """
    Fetches the latest price for a single ticker.
    Returns None if failed.
    """
    try:
        if not ticker.endswith(".JK"):
            ticker = f"{ticker}.JK"
        
        stock = yf.Ticker(ticker)
        # Fast way to get price: fast_info or history 1d
        price = stock.fast_info.last_price
        return price
    except Exception as e:
        print(f"Error fetching price for {ticker}: {e}")
        return None

def get_multiple_prices(tickers):
    """
    Fetches current prices for a list of tickers in batch (optimization).
    Returns a dictionary {ticker: price}.
    """
    if not tickers:
        return {}
    
    # Ensure all have .JK
    formatted_tickers = [t if t.endswith(".JK") else f"{t}.JK" for t in tickers]
    formatted_tickers_str = " ".join(formatted_tickers)
    
    try:
        # yf.download is faster for batch
        data = yf.download(formatted_tickers_str, period="1d", interval="1m", progress=False)['Close'].iloc[-1]
        
        results = {}
        for t in tickers:
            ft = t if t.endswith(".JK") else f"{t}.JK"
            # Handle case where data might be a Series (multiple tickers) or scalar (single ticker)
            if isinstance(data, pd.Series):
                 if ft in data:
                     results[t] = data[ft]
            else:
                 # If only one ticker was requested/returned, data is a float
                 if len(tickers) == 1:
                     results[t] = data
        
        return results
    except Exception as e:
        print(f"Error batch fetching: {e}")
        return {}

def get_idx_tickers_sample():
    """
    Returns a sample list of IDX tickers for testing/MVP.
    TODO: Implement a scraper or file reader for the full 900+ list.
    """
    return [
        "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "UNVR", "ICBP", 
        "GOTO", "ANTM", "ADRO", "DMMX", "BRIS", "BRMS", "BUMI"
    ]
