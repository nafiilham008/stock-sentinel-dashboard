import analysis_engine as ae
import pandas as pd
import numpy as np

def create_mock_data():
    # Create valid synthetic data for testing
    dates = pd.date_range(start="2024-01-01", periods=100)
    data = {
        'Open': np.random.uniform(100, 200, 100),
        'High': np.random.uniform(200, 210, 100),
        'Low': np.random.uniform(90, 100, 100),
        'Close': np.random.uniform(100, 200, 100),
        'Volume': np.random.uniform(1000, 5000, 100)
    }
    df = pd.DataFrame(data, index=dates)
    
    # Force a Hammer pattern at the end
    df.iloc[-1] = [100, 105, 80, 102, 5000] # Open, High, Low, Close, Volume
    # Body = |102-100| = 2
    # Lower Shadow = 100 - 80 = 20 (>= 2*2)
    # Upper Shadow = 105 - 102 = 3 (<= 2) -> Fail? 3 <= 2 is False... 
    # Wait, simple math logic check:
    # Body=2. Lower=20. Upper=3.
    # Hammer Logic: Lower >= 2*Body (20>=4 YES). Upper <= Body (3<=2 NO).
    # Let's adjust to make it a perfect Hammer.
    df.iloc[-1] = [100, 101, 80, 100.5, 5000] 
    # Body = 0.5. Lower = 20. Upper = 0.5. Matches!
    
    return df

def test_indicators():
    print("Testing Smart Indicators...")
    
    # Mock de.get_ticker_data to avoid yfinance call
    original_fetch = ae.de.get_ticker_data
    ae.de.get_ticker_data = lambda ticker, period=None, interval=None: create_mock_data()
    
    try:
        res = ae.analyze_ticker("TEST")
        if res:
            print(f"RSI: {res['rsi']:.2f}")
            print(f"MACD: {res['macd_val']:.2f}")
            print(f"Is Hammer: {res.get('is_hammer')}")
            
            if 'rsi' in res and 'macd_val' in res:
                print("PASS: Indicators calculated.")
            else:
                print("FAIL: Indicators missing.")
                
            if res.get('is_hammer'):
                print("PASS: Hammer detected.")
            else:
                print("FAIL: Hammer detection failed.")
                
        else:
            print("FAIL: Analysis returned None.")
            
    except Exception as e:
        print(f"FAIL: Error during test: {e}")
    finally:
        ae.de.get_ticker_data = original_fetch

if __name__ == "__main__":
    test_indicators()
