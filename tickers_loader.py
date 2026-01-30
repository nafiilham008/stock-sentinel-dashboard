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
    {'ticker': 'BBTN', 'name': 'Bank Tabungan Negara (Persero) Tbk'},
    {'ticker': 'BDMN', 'name': 'Bank Danamon Indonesia Tbk'},
    {'ticker': 'BNGA', 'name': 'Bank CIMB Niaga Tbk'},
    {'ticker': 'BJBR', 'name': 'BPD Jawa Barat dan Banten Tbk'},
    {'ticker': 'BTPS', 'name': 'Bank BTPN Syariah Tbk'},

    # Telco & Tech
    {'ticker': 'TLKM', 'name': 'Telkom Indonesia (Persero) Tbk'},
    {'ticker': 'ISAT', 'name': 'Indosat Tbk'},
    {'ticker': 'EXCL', 'name': 'XL Axiata Tbk'},
    {'ticker': 'GOTO', 'name': 'GoTo Gojek Tokopedia Tbk'},
    {'ticker': 'DMMX', 'name': 'Digital Mediatama Maxima Tbk'},
    {'ticker': 'BUKA', 'name': 'Bukalapak.com Tbk'},
    {'ticker': 'EMTK', 'name': 'Elang Mahkota Teknologi Tbk'},
    {'ticker': 'SCMA', 'name': 'Surya Citra Media Tbk'},
    {'ticker': 'MTDL', 'name': 'Metrodata Electronics Tbk'},
    {'ticker': 'WIFI', 'name': 'Solusi Sinergi Digital Tbk'},

    # Energy, Mining, Oil & Gas
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
    {'ticker': 'HRUM', 'name': 'Harum Energy Tbk'},
    {'ticker': 'INDY', 'name': 'Indika Energy Tbk'},
    {'ticker': 'ELSA', 'name': 'Elnusa Tbk'},
    {'ticker': 'MBMA', 'name': 'Merdeka Battery Materials Tbk'},
    {'ticker': 'NCKL', 'name': 'Trimegah Bangun Persada Tbk'},
    {'ticker': 'AMMN', 'name': 'Amman Mineral Internasional Tbk'},
    {'ticker': 'PSAB', 'name': 'J Resources Asia Pasifik Tbk'},
    {'ticker': 'TINS', 'name': 'Timah Tbk'},
    {'ticker': 'DOID', 'name': 'Delta Dunia Makmur Tbk'},

    # Consumer Goods & Retail
    {'ticker': 'UNVR', 'name': 'Unilever Indonesia Tbk'},
    {'ticker': 'ICBP', 'name': 'Indofood CBP Sukses Makmur Tbk'},
    {'ticker': 'INDF', 'name': 'Indofood Sukses Makmur Tbk'},
    {'ticker': 'MYOR', 'name': 'Mayora Indah Tbk'},
    {'ticker': 'KLBF', 'name': 'Kalbe Farma Tbk'},
    {'ticker': 'HMSP', 'name': 'H.M. Sampoerna Tbk'},
    {'ticker': 'GGRM', 'name': 'Gudang Garam Tbk'},
    {'ticker': 'SIDO', 'name': 'Industri Jamu dan Farmasi Sido Muncul Tbk'},
    {'ticker': 'ACES', 'name': 'Ace Hardware Indonesia Tbk'},
    {'ticker': 'AMRT', 'name': 'Sumber Alfaria Trijaya Tbk'},
    {'ticker': 'MIDI', 'name': 'Midi Utama Indonesia Tbk'},
    {'ticker': 'MAPI', 'name': 'Mitra Adiperkasa Tbk'},
    {'ticker': 'MAPA', 'name': 'Map Aktif Adiperkasa Tbk'},
    {'ticker': 'RALS', 'name': 'Ramayana Lestari Sentosa Tbk'},
    {'ticker': 'LPPF', 'name': 'Matahari Department Store Tbk'},
    {'ticker': 'CMRY', 'name': 'Cisarua Mountain Dairy Tbk'},
    {'ticker': 'CPIN', 'name': 'Charoen Pokphand Indonesia Tbk'},
    {'ticker': 'JPFA', 'name': 'Japfa Comfeed Indonesia Tbk'},
    {'ticker': 'MAIN', 'name': 'Malindo Feedmill Tbk'},

    # Auto, Heavy Equipment & Conglomerates
    {'ticker': 'ASII', 'name': 'Astra International Tbk'},
    {'ticker': 'UNTR', 'name': 'United Tractors Tbk'},
    {'ticker': 'HEXA', 'name': 'Hexindo Adiperkasa Tbk'},
    {'ticker': 'AUTO', 'name': 'Astra Otoparts Tbk'},
    {'ticker': 'IMAS', 'name': 'Indomobil Sukses Internasional Tbk'},
    {'ticker': 'DRMA', 'name': 'Dharma Polimetal Tbk'},

    # Property & Construction
    {'ticker': 'BSDE', 'name': 'Bumi Serpong Damai Tbk'},
    {'ticker': 'CTRA', 'name': 'Ciputra Development Tbk'},
    {'ticker': 'PWON', 'name': 'Pakuwon Jati Tbk'},
    {'ticker': 'SMRA', 'name': 'Summarecon Agung Tbk'},
    {'ticker': 'ASRI', 'name': 'Alam Sutera Realty Tbk'},
    {'ticker': 'APLN', 'name': 'Agung Podomoro Land Tbk'},
    {'ticker': 'PTPP', 'name': 'PP (Persero) Tbk'},
    {'ticker': 'WIKA', 'name': 'Wijaya Karya (Persero) Tbk'},
    {'ticker': 'ADHI', 'name': 'Adhi Karya (Persero) Tbk'},
    {'ticker': 'WEGE', 'name': 'Wijaya Karya Bangunan Gedung Tbk'},

    # Infrastructure, Transport & Utilities
    {'ticker': 'JSMR', 'name': 'Jasa Marga (Persero) Tbk'},
    {'ticker': 'GIAA', 'name': 'Garuda Indonesia (Persero) Tbk'},
    {'ticker': 'BIRD', 'name': 'Blue Bird Tbk'},
    {'ticker': 'SMDR', 'name': 'Samudera Indonesia Tbk'},
    {'ticker': 'TMAS', 'name': 'Temas Tbk'},
    {'ticker': 'POWR', 'name': 'Cikarang Listrindo Tbk'},
    {'ticker': 'KEEN', 'name': 'Kencana Energi Lestari Tbk'},

    # Volatile / "Gorengan" / Others
    {'ticker': 'KAEF', 'name': 'Kimia Farma Tbk'},
    {'ticker': 'INAF', 'name': 'Indofarma Tbk'},
    {'ticker': 'DATA', 'name': 'Remala Abadi Tbk'},
    {'ticker': 'PANI', 'name': 'Pantai Indah Kapuk Dua Tbk'},
    {'ticker': 'CUAN', 'name': 'Petrindo Jaya Kreasi Tbk'},
    {'ticker': 'BREN', 'name': 'Barito Renewables Energy Tbk'},
    {'ticker': 'TPIA', 'name': 'Chandra Asri Pacific Tbk'},
    {'ticker': 'CGAS', 'name': 'Citra Nusantara Gemilang Tbk'},
    {'ticker': 'STRK', 'name': 'Lovina Beach Brewery Tbk'},
    {'ticker': 'FREN', 'name': 'Smartfren Telecom Tbk'},
    {'ticker': 'SRTG', 'name': 'Saratoga Investama Sedaya Tbk'},
    {'ticker': 'TOWR', 'name': 'Sarana Menara Nusantara Tbk'},
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
