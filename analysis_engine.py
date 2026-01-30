import data_engine as de
import pandas as pd

def analyze_ticker(ticker):
    """
    Performs full analysis on a ticker:
    1. ATH Check
    2. Volatility Check
    
    Returns a dict with analysis results.
    """
    if not ticker.endswith(".JK"):
        ticker = f"{ticker}.JK"
        
    try:
        # Fetch 5 years of data for ATH (max is too slow/heavy sometimes, 5y is decent for "modern" ATH)
        # For true ATH we need 'max', but let's try 'max' first and see performance.
        hist = de.get_ticker_data(ticker, period="max", interval="1d")
        
        if hist.empty:
            return None
        
        # --- ATH Logic ---
        ath_price = hist['High'].max()
        ath_date = hist['High'].idxmax().strftime('%Y-%m-%d')
        last_price = hist['Close'].iloc[-1]
        
        # Calculate Distance to ATH (negative means below ATH)
        # If Current = 100, ATH = 200, Distance = -50%
        # If Current = 200, ATH = 200, Distance = 0% (Breakout!)
        distance_pct = ((last_price - ath_price) / ath_price) * 100
        
        is_breakout = distance_pct >= -2.0 # Near ATH (within 2%)
        
        # --- Volatility Logic ---
        # Compare last volume vs 20-day average volume
        recent_data = hist.tail(21) # Get last 21 days
        if len(recent_data) < 2:
            return None
            
        avg_volume = recent_data['Volume'].iloc[:-1].mean()
        last_volume = recent_data['Volume'].iloc[-1]
        
        # Avoid division by zero
        if avg_volume == 0:
            vol_spike_ratio = 1.0
        else:
            vol_spike_ratio = last_volume / avg_volume
            
        # Price Change
        price_change_pct = ((recent_data['Close'].iloc[-1] - recent_data['Close'].iloc[-2]) / recent_data['Close'].iloc[-2]) * 100
        
        is_volatile = (vol_spike_ratio > 3.0) or (abs(price_change_pct) > 5.0)
        
        return {
            'ticker': ticker.replace('.JK', ''),
            'current_price': last_price,
            'ath_price': ath_price,
            'ath_date': ath_date,
            'ath_distance_pct': distance_pct,
            'is_breakout': is_breakout,
            'vol_spike_ratio': vol_spike_ratio,
            'price_change_pct': price_change_pct,
            'is_volatile': is_volatile
        }
        
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def scan_market(tickers_list):
    """
    Iterates through a list of tickers and returns meaningful results.
    """
    results = []
    print(f"Scanning {len(tickers_list)} tickers...")
    
    # In a real scenario, we might want to parallelize this or use batch requests properly.
    # For now, sequential is fine for 50 tickers.
    for t in tickers_list:
        data = analyze_ticker(t)
        if data:
            results.append(data)
            
    return pd.DataFrame(results)
