import requests
import database_manager as db
import pandas as pd

# Fallback list containing LQ45 (Liquid 45) + Popular Volatile Stocks
# This ensures we have a representative market sample ~50-60 stocks.
STATIC_TICKERS = [
    # Banks (Big Caps)
    {'ticker': 'BBCA', 'name': 'Bank Central Asia Tbk'},
    {'ticker': 'BBRI', 'name': 'Bank Rakyat Indonesia (Persero) Tbk'},
    {'ticker': 'BMRI', 'name': 'Bank Mandiri (Persero) Tbk'},
    {'ticker': 'BBNI', 'name': 'Bank Negara Indonesia (Persero) Tbk'},
    {'ticker': 'BRIS', 'name': 'Bank Syariah Indonesia Tbk'},
    {'ticker': 'ARTO', 'name': 'Bank Jago Tbk'},

    # Telco & Tech
    {'ticker': 'TLKM', 'name': 'Telkom Indonesia (Persero) Tbk'},
    {'ticker': 'ISAT', 'name': 'Indosat Tbk'},
    {'ticker': 'EXCL', 'name': 'XL Axiata Tbk'},
    {'ticker': 'GOTO', 'name': 'GoTo Gojek Tokopedia Tbk'},
    {'ticker': 'DMMX', 'name': 'Digital Mediatama Maxima Tbk'},
    {'ticker': 'BUKA', 'name': 'Bukalapak.com Tbk'},
    {'ticker': 'EMTK', 'name': 'Elang Mahkota Teknologi Tbk'},

    # Energy & Mining (Commodities)
    {'ticker': 'ADRO', 'name': 'Adaro Energy Indonesia Tbk'},
    {'ticker': 'PTBA', 'name': 'Bukit Asam Tbk'},
    {'ticker': 'ITMG', 'name': 'Indo Tambangraya Megah Tbk'},
    {'ticker': 'BUMI', 'name': 'Bumi Resources Tbk'},
    {'ticker': 'BRMS', 'name': 'Bumi Resources Minerals Tbk'},
    {'ticker': 'ANTM', 'name': 'Aneka Tambang Tbk'},
    {'ticker': 'INCO', 'name': 'Vale Indonesia Tbk'},
    {'ticker': 'MDKA', 'name': 'Merdeka Copper Gold Tbk'},
    {'ticker': 'PGAS', 'name': 'Perusahaan Gas Negara Tbk'},
    {'ticker': 'AKRA', 'name': 'AKR Corporindo Tbk'},
    {'ticker': 'MEDC', 'name': 'Medco Energi Internasional Tbk'},

    # Consumer Goods
    {'ticker': 'UNVR', 'name': 'Unilever Indonesia Tbk'},
    {'ticker': 'ICBP', 'name': 'Indofood CBP Sukses Makmur Tbk'},
    {'ticker': 'INDF', 'name': 'Indofood Sukses Makmur Tbk'},
    {'ticker': 'MYOR', 'name': 'Mayora Indah Tbk'},
    {'ticker': 'KLBF', 'name': 'Kalbe Farma Tbk'},
    {'ticker': 'HMSP', 'name': 'H.M. Sampoerna Tbk'},
    {'ticker': 'GGRM', 'name': 'Gudang Garam Tbk'},

    # Auto & Conglomerates
    {'ticker': 'ASII', 'name': 'Astra International Tbk'},
    {'ticker': 'UNTR', 'name': 'United Tractors Tbk'},

    # Property & Construction
    {'ticker': 'BSDE', 'name': 'Bumi Serpong Damai Tbk'},
    {'ticker': 'CTRA', 'name': 'Ciputra Development Tbk'},
    {'ticker': 'PWON', 'name': 'Pakuwon Jati Tbk'},
    {'ticker': 'SMRA', 'name': 'Summarecon Agung Tbk'},

    # Usually Volatile / "Gorengan" Candidates (for testing Scanner)
    {'ticker': 'KAEF', 'name': 'Kimia Farma Tbk'},
    {'ticker': 'INAF', 'name': 'Indofarma Tbk'},
    {'ticker': 'DATA', 'name': 'Remala Abadi Tbk'},
    {'ticker': 'PANI', 'name': 'Pantai Indah Kapuk Dua Tbk'},
    {'ticker': 'CUAN', 'name': 'Petrindo Jaya Kreasi Tbk'},
    {'ticker': 'BREN', 'name': 'Barito Renewables Energy Tbk'},
    {'ticker': 'TPIA', 'name': 'Chandra Asri Pacific Tbk'},
    {'ticker': 'CGAS', 'name': 'Citra Nusantara Gemilang Tbk'},
]

def fetch_tickers_from_web():
    """
    Simulation of fetching from web. Returns the static list for now.
    """
    print("Using Verified Static List (LQ45 + Popular)")
    return STATIC_TICKERS

def update_master_stocks():
    """
    Updates the master_stocks table in SQLite with the latest list.
    """
    tickers = fetch_tickers_from_web()
    
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    count_new = 0
    for t in tickers:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO master_stocks (ticker, company_name)
                VALUES (?, ?)
            ''', (t['ticker'], t['name']))
            if cursor.rowcount > 0:
                count_new += 1
        except Exception as e:
            print(f"Error inserting {t['ticker']}: {e}")
            
    conn.commit()
    conn.close()
    
    print(f"Database updated. Added {count_new} new tickers. Total managed: {len(tickers)}")
    return len(tickers)

if __name__ == "__main__":
    db.init_db()
    update_master_stocks()
