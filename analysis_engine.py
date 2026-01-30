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

        # --- Trade Plan (Suggestion) ---
        # Plan A: Conservative Swing (Risk 4%, Reward 8% -> Ratio 1:2)
        sl_cons = int(last_price * 0.96)
        tp_cons = int(last_price * 1.08)
        
        # Plan B: Aggressive Trend (Risk 5%, Reward 15% -> Ratio 1:3)
        sl_aggr = int(last_price * 0.95)
        tp_aggr = int(last_price * 1.15)
        
        # Rounding
        sl_cons = round(sl_cons / 5) * 5
        tp_cons = round(tp_cons / 5) * 5
        sl_aggr = round(sl_aggr / 5) * 5
        tp_aggr = round(tp_aggr / 5) * 5

        # --- Smart Indicators (RSI, MACD, EMA) ---
        # RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        # MACD (12, 26, 9)
        ema12 = hist['Close'].ewm(span=12, adjust=False).mean()
        ema26 = hist['Close'].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        
        # EMA Trend
        ema50 = hist['Close'].ewm(span=50, adjust=False).mean()
        ema200 = hist['Close'].ewm(span=200, adjust=False).mean()
        current_ema50 = ema50.iloc[-1]
        current_ema200 = ema200.iloc[-1]

        # Signals
        is_oversold = current_rsi < 30
        is_golden_cross = (macd_line.iloc[-2] < signal_line.iloc[-2]) and (current_macd > current_signal)
        uptrend = current_ema50 > current_ema200

        # --- Candlestick Patterns ---
        open_p = hist['Open'].iloc[-1]
        close_p = hist['Close'].iloc[-1]
        high_p = hist['High'].iloc[-1]
        low_p = hist['Low'].iloc[-1]
        
        body = abs(close_p - open_p)
        range_len = high_p - low_p
        upper_shadow = high_p - max(open_p, close_p)
        lower_shadow = min(open_p, close_p) - low_p
        
        is_doji = (body <= range_len * 0.05) and (range_len > 0)
        # Hammer: Small body at top, long lower shadow (> 60% of total length)
        # Upper shadow must be small (< 10% of total length)
        is_hammer = (lower_shadow >= range_len * 0.6) and (upper_shadow <= range_len * 0.1)

        # --- Multi-Timeframe Analysis (Weekly Trend) ---
        # Fetch 2y weekly data to check major trend
        hist_wk = de.get_ticker_data(ticker, period="2y", interval="1wk")
        
        trend_strength = "NEUTRAL"
        if not hist_wk.empty and len(hist_wk) > 20:
             # Calculate Weekly EMA 20 (Standard for medium-term trend)
             ema20_wk = hist_wk['Close'].ewm(span=20, adjust=False).mean()
             current_ema20_wk = ema20_wk.iloc[-1]
             last_price_wk = hist_wk['Close'].iloc[-1]
             
             is_weekly_uptrend = last_price_wk > current_ema20_wk
             
             if is_weekly_uptrend and uptrend: # Both Daily & Weekly UP
                 trend_strength = "STRONG UPTREND 🚀"
             elif is_weekly_uptrend:
                 trend_strength = "MILD UPTREND (Pullback) 🌤️"
             elif uptrend:
                 trend_strength = "WEAK UPTREND (Reversal?) ☁️"
             else:
                 trend_strength = "DOWNTREND 🌧️"
        else:
             trend_strength = "UNKNOWN"

        return {
            'ticker': ticker.replace('.JK', ''),
            'current_price': last_price,
            'ath_price': ath_price,
            'ath_date': ath_date,
            'ath_distance_pct': distance_pct,
            'is_breakout': is_breakout,
            'vol_spike_ratio': vol_spike_ratio,
            'price_change_pct': price_change_pct,
            'is_volatile': is_volatile,
            'rsi': current_rsi,
            'macd_val': current_macd,
            'signal_val': current_signal,
            'is_oversold': is_oversold,
            'is_golden_cross': is_golden_cross,
            'is_uptrend': uptrend,
            'trend_strength': trend_strength,
            'is_weekly_uptrend': is_weekly_uptrend if 'is_weekly_uptrend' in locals() else False,
            'is_doji': is_doji,
            'is_hammer': is_hammer,
            'plan_cons_sl': sl_cons,
            'plan_cons_tp': tp_cons,
            'plan_aggr_sl': sl_aggr,
            'plan_aggr_tp': tp_aggr
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
