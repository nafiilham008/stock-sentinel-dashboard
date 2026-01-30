import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "stock_sentinel.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    return conn

def init_db():
    """Initializes the database functionality by creating necessary tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Master Stocks Table (For reference/caching if needed)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS master_stocks (
            ticker TEXT PRIMARY KEY,
            company_name TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Portfolio Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            buy_price REAL,
            target_price REAL,
            cutloss_price REAL,
            notes TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker)
        )
    ''')

    # Settings Table (For storing bot tokens, chat IDs, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Latest Scan Results Table (For persistence)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS latest_scan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            data_json TEXT,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# --- Scan Result Persistence ---
import json

def save_scan_results(df_results):
    """Saves the dataframe results to DB as JSON."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Clear old results
        cursor.execute("DELETE FROM latest_scan")
        
        # Insert new results
        if not df_results.empty:
            for _, row in df_results.iterrows():
                data_str = json.dumps(row.to_dict())
                cursor.execute("INSERT INTO latest_scan (ticker, data_json) VALUES (?, ?)", (row['ticker'], data_str))
        
        conn.commit()
    finally:
        conn.close()

def get_latest_scan_results():
    """Retrieves the latest scan results from DB."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT data_json, scan_time FROM latest_scan")
        rows = cursor.fetchall()
        
        if not rows:
            return pd.DataFrame(), None
            
        data_list = [json.loads(r[0]) for r in rows]
        last_time = rows[0][1] # Get timestamp from first row
        return pd.DataFrame(data_list), last_time
    except Exception as e:
        print(f"Error loading scan results: {e}")
        return pd.DataFrame(), None
    finally:
        conn.close()

# --- Portfolio Functions ---
def add_portfolio_item(ticker, buy_price, target_price=None, cutloss_price=None, notes=""):
    """Adds or updates a stock in the portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO portfolio (ticker, buy_price, target_price, cutloss_price, notes)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                buy_price=excluded.buy_price,
                target_price=excluded.target_price,
                cutloss_price=excluded.cutloss_price,
                notes=excluded.notes
        ''', (ticker.upper(), buy_price, target_price, cutloss_price, notes))
        conn.commit()
        return True, "Success"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def get_portfolio():
    """Retrieves all portfolio items as a DataFrame."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM portfolio", conn)
        return df
    except Exception:
        return pd.DataFrame() # Return empty if error or empty
    finally:
        conn.close()

def delete_portfolio_item(ticker):
    """Deletes a stock from the portfolio."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM portfolio WHERE ticker = ?", (ticker.upper(),))
        conn.commit()
    finally:
        conn.close()

def get_all_tickers():
    """Retrieves all tickers from the master_stocks table."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ticker FROM master_stocks")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"Error getting tickers: {e}")
        return []
    finally:
        conn.close()

def set_setting(key, value):
    """Saves a setting to the database."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        ''', (key, value))
        conn.commit()
    finally:
        conn.close()

def get_setting(key):
    """Retrieves a setting value."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()

def add_master_stock(ticker, name="Custom"):
    """Adds a new ticker to the master_stocks table."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO master_stocks (ticker, company_name)
            VALUES (?, ?)
        ''', (ticker.upper(), name))
        return cursor.rowcount > 0
    finally:
        conn.commit()
        conn.close()

def delete_master_stock(ticker):
    """Removes a ticker from the master_stocks table."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM master_stocks WHERE ticker = ?", (ticker.upper(),))
    finally:
        conn.commit()
        conn.close()

if __name__ == "__main__":
    init_db()
