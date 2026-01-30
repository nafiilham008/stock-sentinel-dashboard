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
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

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

if __name__ == "__main__":
    init_db()
