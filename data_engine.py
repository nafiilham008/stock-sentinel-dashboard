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

# --- Market Radar (IHSG & News) ---
import requests
import xml.etree.ElementTree as ET

def get_market_radar():
    """
    Fetches IHSG (Composite) data and Sentiment from News.
    """
    # 1. Get IHSG Data
    ihsg_ticker = "^JKSE"
    try:
        ihsg = yf.Ticker(ihsg_ticker)
        # Get 5d history to calculate changes
        hist = ihsg.history(period="5d")
        
        current_price = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        # Determine status
        if change_pct < -2.0:
            status = "CRASH"
        elif change_pct < -1.0:
            status = "CORRECTION"
        elif change_pct > 1.0:
            status = "BULLISH"
        else:
            status = "NEUTRAL"
            
    except Exception as e:
        print(f"IHSG Data Error: {e}")
        current_price = 0
        change_pct = 0
        status = "UNKNOWN"

    # 2. Get News Sentiment (RSS Google News)
    news_sentiment = "NEUTRAL"
    top_headlines = []
    
    try:
        # RSS Feed for "IHSG" topic in Indonesia
        url = "https://news.google.com/rss/search?q=IHSG+Saham+Indonesia+when:1d&hl=id&gl=ID&ceid=ID:id"
        resp = requests.get(url, timeout=5)
        
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            
            # Keywords
            panic_words = ["anjlok", "ambles", "turun tajam", "merah membara", "crash", "panic", "tak berdaya", "terjun"]
            bad_words = ["melemah", "koreksi", "waspada", "asing keluar", "net sell"]
            good_words = ["menguat", "rebound", "hijau", "naik", "rekor", "tertinggi"]
            
            score = 0
            count = 0
            
            for item in root.findall(".//item")[:5]: # Check top 5 news
                title = item.find("title").text
                link = item.find("link").text
                pubDate = item.find("pubDate").text
                
                title_lower = title.lower()
                
                # Scoring
                if any(w in title_lower for w in panic_words):
                    score -= 3
                elif any(w in title_lower for w in bad_words):
                    score -= 1
                elif any(w in title_lower for w in good_words):
                    score += 1
                    
                top_headlines.append({"title": title, "link": link, "date": pubDate})
                count += 1
            
            # Determine Sentiment from Score
            if score <= -3:
                news_sentiment = "PANIC / FEAR 😱"
            elif score < 0:
                news_sentiment = "NEGATIVE 😟"
            elif score > 2:
                news_sentiment = "OPTIMISTIC 🤩"
            elif score >= 0:
                news_sentiment = "NEUTRAL 😐"
                
    except Exception as e:
        print(f"News Fetch Error: {e}")
        top_headlines.append({"title": "Failed to fetch news", "link": "#", "date": ""})

    return {
        "ihsg_price": current_price,
        "ihsg_prev": prev_close,
        "ihsg_change": change_pct,
        "market_status": status,
        "sentiment": news_sentiment,
        "headlines": top_headlines
    }

def get_ticker_news(ticker):
    """
    Fetches latest news for a specific ticker.
    """
    news_list = []
    try:
        # Search query: "BBTN Saham" or similar
        query = f"{ticker.replace('.JK', '')}+Saham"
        url = f"https://news.google.com/rss/search?q={query}+when:7d&hl=id&gl=ID&ceid=ID:id"
        
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:2]: # Get top 2
                title = item.find("title").text
                link = item.find("link").text
                news_list.append({"title": title, "link": link})
    except:
        pass
        
    return news_list
