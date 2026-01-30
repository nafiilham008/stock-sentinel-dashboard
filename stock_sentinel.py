import streamlit as st
import pandas as pd
import database_manager as db
import data_engine as de
import analysis_engine as ae
import chart_engine as ce
import telegram_bot as bot

# --- Page Config ---
st.set_page_config(page_title="Stock Sentinel Dashboard", page_icon="📈", layout="wide")

# --- Initialize ---
if 'db_init' not in st.session_state:
    db.init_db()
    st.session_state['db_init'] = True

if 'scan_results' not in st.session_state:
    # Try to load latest from DB
    last_df, last_time = db.get_latest_scan_results()
    if not last_df.empty:
        st.session_state['scan_results'] = last_df
        st.toast(f"Loaded previous scan from {last_time}")
    else:
        st.session_state['scan_results'] = pd.DataFrame()

# --- Functions ---
def run_scanner():
    """Runs the market scan and updates session state."""
    all_tickers = db.get_all_tickers()
    if not all_tickers:
        return pd.DataFrame()
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(all_tickers)
    for i, ticker in enumerate(all_tickers):
        status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
        res = ae.analyze_ticker(ticker)
        if res:
            results.append(res)
        progress_bar.progress((i + 1) / total)
        
    status_text.empty()
    progress_bar.empty()
    
    df = pd.DataFrame(results)
    st.session_state['scan_results'] = df
    # Save to DB for persistence
    db.save_scan_results(df)
    return df

# --- Sidebar ---
st.sidebar.title("🛡️ Stock Sentinel")
st.sidebar.markdown("---")
# Quick Actions
if st.sidebar.button("🔄 Refresh Market Feed"):
    run_scanner()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Settings")
curr_token = db.get_setting("TELEGRAM_BOT_TOKEN")
if not curr_token:
    st.sidebar.warning("⚠ Bot Token Missing")
else:
    st.sidebar.success("✅ Bot Connected")

# --- Background Scheduler ---
import threading
import time
from datetime import datetime, time as time_obj

@st.cache_resource
def get_scheduler_state():
    return {"running": False, "thread": None, "start_hour": 9, "start_minute": 0}

scheduler = get_scheduler_state()

def background_scan_job(interval_sec=1800, start_h=9, start_m=0):
    """Runs in background thread. Scans and sends Telegram alerts."""
    while scheduler["running"]:
        now = datetime.now()
        current_time = now.time()
        start_time = time_obj(start_h, start_m)
        
        # Only run if current time >= start_time (simple logic for daily start)
        # For simplicity, we just run loop and check constraint
        
        try:
            print("Running background scan...")
            tickers = db.get_all_tickers()
            if tickers:
                results = []
                for t in tickers:
                    res = ae.analyze_ticker(t)
                    if res:
                        results.append(res)
                
                df = pd.DataFrame(results)
                if not df.empty:
                    # Save to DB for UI sync
                    db.save_scan_results(df)
                    
                    # Filter for alerts
                    # 1. Breakouts
                    df_ath = df[df['ath_distance_pct'] > -2.0]
                    if not df_ath.empty:
                        bot.send_scan_report("Breakout Alert 🚀", df_ath)
                    
                    # 2. RSI Oversold
                    df_rsi = df[df.get('is_oversold', False) == True]
                    if not df_rsi.empty:
                        bot.send_scan_report("Oversold Alert (RSI < 30) 📉", df_rsi)

                    # 3. Golden Cross
                    df_gc = df[df.get('is_golden_cross', False) == True]
                    if not df_gc.empty:
                         bot.send_scan_report("Golden Cross Alert ✨", df_gc)

        except Exception as e:
            print(f"Background scan error: {e}")
            
        # Smart Sleep (Check every second to allow immediate stop)
        for _ in range(int(interval_sec)):
            if not scheduler["running"]:
                print("Stopping background scan...")
                break
            time.sleep(1)

st.sidebar.markdown("### ⏲️ Auto-Pilot")
col_int, col_start = st.sidebar.columns(2)

# Load saved settings
saved_int = db.get_setting("SCAN_INTERVAL")
def_int = int(saved_int) if saved_int else 30

saved_start = db.get_setting("SCAN_START_HOUR")
def_start = int(saved_start) if saved_start else 9

# Render widgets
scan_interval = col_int.slider("Interval (Min)", 5, 60, def_int, step=5)
start_hour = col_start.number_input("Start Hour", 0, 23, def_start)

# Save if changed
if scan_interval != def_int:
    db.set_setting("SCAN_INTERVAL", str(scan_interval))

if start_hour != def_start:
    db.set_setting("SCAN_START_HOUR", str(start_hour))

run_auto = st.sidebar.toggle(f"Enable Background", value=scheduler["running"])

if run_auto and not scheduler["running"]:
    scheduler["running"] = True
    # Pass arguments
    t = threading.Thread(target=background_scan_job, args=(scan_interval * 60, start_hour, 0), daemon=True)
    t.start()
    scheduler["thread"] = t
    st.sidebar.info(f"Scanner started. Interval: {scan_interval}m, Start: {start_hour}:00")
elif not run_auto and scheduler["running"]:
    scheduler["running"] = False
    st.sidebar.warning("Stopped background scanner.")

# --- RISKS CALCULATOR (NEW) ---
with st.sidebar.expander("🧮 Calculator (Risk Manager)"):
    st.caption("Calculate Safe Position Size")
    cap = st.number_input("Capital (Rp)", value=1000000)
    risk_pct = st.slider("Risk per Trade (%)", 0.5, 5.0, 2.0)
    entry = st.number_input("Entry Price", value=0)
    stop_loss = st.number_input("Stop Loss Price", value=0)
    
    if entry > stop_loss and stop_loss > 0:
        risk_amt = cap * (risk_pct / 100)
        risk_per_share = entry - stop_loss
        shares = risk_amt / risk_per_share
        lots = int(shares / 100)
        
        st.info(f"Risk Amount: **Rp {risk_amt:,.0f}**")
        st.success(f"Max Buy: **{lots} Lots**")
    elif entry > 0:
         st.warning("Ensure Entry > Stop Loss")

# Navigation for cleanup (Portfolio Manager moved to sidebar expander or kept as separate if too complex, 
# for now let's keep Portfolio Manager as a separate page optionally, or integrate it. 
# Plan said "Unified", so let's try to make it single page or minimal Nav)
# To keep it simple, I will keep 'Portfolio Manager' as a separate "Admin" page in sidebar, 
# but the main page is "Dashboard" (Unified).

page = st.sidebar.radio("Menu", ["Dashboard (Live)", "Portfolio Manager", "Settings"])

# --- MAIN PAGE: DASHBOARD (UNIFIED) ---
if page == "Dashboard (Live)":
    st.title("🛡️ Trading Station")

    # --- SECTION 0: MARKET RADAR (SENTIMENT) ---
    radar = de.get_market_radar()
    
    # Custom CSS for status
    color = "green" if radar['ihsg_change'] >= 0 else "red"
    sent_color = "green" if "OPTIMISTIC" in radar['sentiment'] else ("red" if "PANIC" in radar['sentiment'] else "gray")

    with st.container(border=True):
        col_idx, col_sent = st.columns(2)
        with col_idx:
            st.metric("IHSG (Composite Index)", 
                      f"{radar['ihsg_price']:,.2f}", 
                      f"{radar['ihsg_change']:.2f}%")
            st.caption(f"Prev: {radar['ihsg_prev']:,.2f}")
        
        with col_sent:
            st.write(f"**Sentimen Pasar (Sentiment)**: :{sent_color}[{radar['sentiment']}]")
            st.caption(f"Status: {radar['market_status']}")
    
        with st.expander("📰 Berita Terkini (Market Headlines)"):
            for news in radar['headlines']:
                st.markdown(f"- [{news['title']}]({news['link']}) _({news['date']})_")

    # --- SECTION 1: LIVE MARKET FEED (TOP) ---
    st.markdown("### 📡 Live Market Signal (Feed)")
    
    # Auto-run scanner if empty (First load)
    if st.session_state['scan_results'].empty:
        if st.button("▶ Start Market Feed"):
            run_scanner()
            st.rerun()
        st.info("Market feed not active. Click Start to scan.")
    else:
        df_res = st.session_state['scan_results']
        
        # Backward compatibility for new columns
        if 'trend_strength' not in df_res.columns:
            df_res['trend_strength'] = "N/A"
            
        # --- BEST PICK ALGORITHM ---
        # Criteria: Golden Cross AND Strong Uptrend (Weekly + Daily Up)
        df_picks = df_res[
            (df_res['is_golden_cross'] == True) & 
            (df_res['trend_strength'].str.contains("STRONG", na=False))
        ]
        
        # Fallback: If no strong, try just Uptrend or just Golden Cross
        if df_picks.empty:
             df_picks = df_res[df_res['is_golden_cross'] == True]
        
        # Limit to top 3
        df_picks = df_picks.head(3)
        
        if not df_picks.empty:
            st.markdown("#### 🏆 AI Top Picks (Recommendation)")
            
            # Use 3 cols for compact view
            cols = st.columns(3)
            for i, (idx, row) in enumerate(df_picks.iterrows()):
                # Distribute cards across columns
                with cols[i % 3]: 
                    with st.container(border=True):
                        # Header
                        c1, c2 = st.columns([2, 1])
                        c1.subheader(f"{row['ticker']}")
                        c2.markdown(f"**Rp {row['current_price']:,.0f}**")
                        st.caption(f"{row['trend_strength']}")
                        
                        # Plan (Compact)
                        st.markdown(f"""
                        **🎯 Plan A (Safe 1:2)**
                        - Buy: **{row['current_price']:,.0f}**
                        - TP: **{row['plan_cons_tp']:,.0f}** :green[(+8%)]
                        - SL: **{row['plan_cons_sl']:,.0f}** :red[(-4%)]
                        
                        **🚀 Plan B (Aggressive 1:3)**
                        - TP: **{row['plan_aggr_tp']:,.0f}** :green[(+15%)]
                        - SL: **{row['plan_aggr_sl']:,.0f}** :red[(-5%)]
                        """)
                        
                        # News
                        stock_news = de.get_ticker_news(row['ticker'])
                        if stock_news:
                            st.markdown("---")
                            st.caption("🗞️ Related News:")
                            for n in stock_news:
                                st.markdown(f"- [{n['title'][:50]}...]({n['link']})")

        # Split into 2 cols: Breakout & Volatile
        col_bo, col_vol = st.columns(2)
        
        with col_bo:
            st.markdown("#### 🚀 Potential Breakout (Near ATH)")
            st.caption("Saham yang harganya mendekati Rekor Tertinggi (ATH). Menandakan tren naik sangat kuat.")
            df_ath = df_res[df_res['ath_distance_pct'] > -10].sort_values('ath_distance_pct', ascending=False).head(5)
            if not df_ath.empty:
                st.dataframe(
                    df_ath[['ticker', 'current_price', 'ath_distance_pct', 'trend_strength']]
                    .rename(columns={'ticker': 'Ticker', 'current_price': 'Price', 'ath_distance_pct': 'ATH Dist', 'trend_strength': 'Trend (W+D)'})
                    .style.format({"Price": "{:,.0f}", "ATH Dist": "{:.2f}%"}),
                    use_container_width=True,
                    height=200
                )
            else:
                st.caption("No breakouts detected.")

        with col_vol:
            st.markdown("#### ⚡ Volatility Alert")
            st.caption("Saham yang volume atau harganya bergerak drastis. Hati-hati, High Risk High Reward.")
            df_vol = df_res[df_res['is_volatile'] == True].head(5)
            if not df_vol.empty:
                st.dataframe(
                    df_vol[['ticker', 'current_price', 'vol_spike_ratio', 'trend_strength']]
                    .rename(columns={'ticker': 'Ticker', 'current_price': 'Price', 'vol_spike_ratio': 'Vol Ratio', 'trend_strength': 'Trend (W+D)'})
                    .style.format({"Price": "{:,.0f}", "Vol Ratio": "{:.1f}x"}),
                    use_container_width=True,
                    height=200
                )
            else:
                st.caption("Market is calm.")

        # --- SMART ALERTS (NEW) ---
        st.markdown("#### 🧠 Smart Signals (Assist)")
        col_rsi, col_macd = st.columns(2)
        
        with col_rsi:
            st.info("📉 Discount Alert (RSI < 30)")
            st.caption("Saham 'Oversold' (Jenuh Jual). Harganya sudah dianggap murah, potensi mantul naik.")
            df_oversold = df_res[df_res['is_oversold'] == True].head(5)
            if not df_oversold.empty:
                 st.dataframe(
                    df_oversold[['ticker', 'current_price', 'rsi', 'trend_strength']]
                    .rename(columns={'ticker': 'Ticker', 'current_price': 'Price', 'rsi': 'RSI', 'trend_strength': 'Trend (W+D)'})
                    .style.format({"Price": "{:,.0f}", "RSI": "{:.1f}"}),
                    use_container_width=True,
                    height=200
                 )
            else:
                st.caption("No oversold stocks found.")

        with col_macd:
            st.success("✨ Trend Reversal (Golden Cross)")
            st.caption("Garis MACD memotong ke atas. Sinyal awal perubahan tren menjadi naik (Uptrend).")
            df_gc = df_res[df_res['is_golden_cross'] == True].head(5)
            if not df_gc.empty:
                st.dataframe(
                    df_gc[['ticker', 'current_price', 'macd_val', 'trend_strength']]
                    .rename(columns={'ticker': 'Ticker', 'current_price': 'Price', 'macd_val': 'MACD', 'trend_strength': 'Trend (W+D)'})
                    .style.format({"Price": "{:,.0f}", "MACD": "{:.2f}"}),
                    use_container_width=True,
                    height=200
                )
            else:
                 st.caption("No reversals detected.")

        # --- CANDLESTICK PATTERNS ---
        st.markdown("#### 🕯️ Candlestick Patterns (Learning)")
        col_hammer, col_doji = st.columns(2)
        
        with col_hammer:
            st.warning("🔨 Hammer (Potential Bottom)")
            st.caption("Pola 'Palu'. Sempat turun dalam tapi dilawan naik. Sinyal kuat harga akan berbalik naik.")
            df_hammer = df_res[df_res.get('is_hammer', False) == True].head(5)
            if not df_hammer.empty:
                 st.dataframe(
                    df_hammer[['ticker', 'current_price']]
                    .rename(columns={'ticker': 'Ticker (Kode)', 'current_price': 'Price (Harga)'})
                    .style.format({"Price (Harga)": "{:,.0f}"}),
                    use_container_width=True,
                    height=150
                 )
            else:
                 st.caption("No hammer patterns.")

        with col_doji:
            st.info("➕ Doji (Indecision)")
            st.caption("Pola 'Indecision'. Penjual dan pembeli sama kuat. Pasar sedang galau menunggu arah.")
            df_doji = df_res[df_res.get('is_doji', False) == True].head(5)
            if not df_doji.empty:
                st.dataframe(
                    df_doji[['ticker', 'current_price']]
                    .rename(columns={'ticker': 'Ticker (Kode)', 'current_price': 'Price (Harga)'})
                    .style.format({"Price (Harga)": "{:,.0f}"}),
                    use_container_width=True,
                    height=150
                )
            else:
                st.caption("No doji patterns.")

    st.divider()

    # --- SECTION 2: CHARTS & PORTFOLIO (SPLIT) ---
    col_main, col_chart = st.columns([1, 1.5])

    with col_main:
        st.markdown("### 💼 My Portfolio")
        df_port = db.get_portfolio()
        
        if not df_port.empty:
            st.dataframe(
                df_port[['ticker', 'buy_price', 'notes']]
                .rename(columns={'ticker': 'Ticker (Kode)', 'buy_price': 'Buy Price (Harga Beli)', 'notes': 'Notes (Catatan)'})
                .style.format({"Buy Price (Harga Beli)": "Rp {:,.0f}"}),
                use_container_width=True
            )
            
            # Selection for Chart
            start_list = df_port['ticker'].tolist()
            # Combine with scan results for selection
            scan_tickers = []
            if not st.session_state['scan_results'].empty:
                 scan_tickers = st.session_state['scan_results']['ticker'].tolist()
            
            full_list = sorted(list(set(start_list + scan_tickers)))
            
            selected_ticker = st.selectbox("Select Stock to Analyze", full_list)
        else:
            st.info("Portfolio empty.")
            selected_ticker = None
            if not st.session_state['scan_results'].empty:
                 # If portfolio empty, allow picking from scan results
                 selected_ticker = st.selectbox("Select Stock to Analyze", st.session_state['scan_results']['ticker'].unique())

    with col_chart:
        st.markdown("### 📈 Technical Chart")
        if selected_ticker:
            st.caption(f"Showing 3-month history for {selected_ticker}")
            fig = ce.create_price_chart(selected_ticker)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Chart data unavailable.")
        else:
            st.info("Select a stock to view chart.")

# --- PAGE: PORTFOLIO MANAGER (Keep as is / Simplified) ---
elif page == "Portfolio Manager":
    st.title("📝 Portfolio Manager")
    
    with st.expander("Add New Stock", expanded=True):
        with st.form("add_stock_form"):
            col1, col2 = st.columns(2)
            ticker_input = col1.text_input("Ticker", "").upper()
            buy_price_input = col2.number_input("Avg Price", min_value=0, step=10)
            notes_input = st.text_area("Notes")
            if st.form_submit_button("Add"):
                if ticker_input:
                    db.add_portfolio_item(ticker_input, buy_price_input, notes=notes_input)
                    st.success(f"Added {ticker_input}")
                    st.rerun()

    st.subheader("Current Holdings")
    df_portfolio = db.get_portfolio()
    if not df_portfolio.empty:
        st.dataframe(df_portfolio)
        
        st.write("🗑️ Remove Stock")
        t_del = st.selectbox("Remove Ticker", df_portfolio['ticker'].tolist())
        if st.button("Delete"):
            db.delete_portfolio_item(t_del)
            st.rerun()

# --- PAGE: SETTINGS ---
elif page == "Settings":
    st.title("⚙️ Settings")
    
    current_token = db.get_setting("TELEGRAM_BOT_TOKEN") or ""
    current_chat_id = db.get_setting("TELEGRAM_CHAT_ID") or ""
    
    with st.expander("🤖 Bot Configuration", expanded=True):
        with st.form("settings"):
            t_in = st.text_input("Bot Token", current_token, type="password")
            c_in = st.text_input("Chat ID", current_chat_id)
            if st.form_submit_button("Save"):
                bot.setup_credentials(t_in, c_in)
                st.success("Saved.")
            
    if st.button("Test Alert"):
        bot.send_telegram_message("🔔 Test from Unified Dashboard.")

    st.markdown("---")
    st.subheader("📋 Manage Watchlist (Monitored Stocks)")
    
    # Add Stock
    col_add, col_list = st.columns([1, 2])
    with col_add:
        st.write("Add Stock to Monitor")
        new_ticker = st.text_input("Ticker Code", "").upper()
        if st.button("Add to Watchlist"):
            if new_ticker:
                if db.add_master_stock(new_ticker):
                     st.success(f"Added {new_ticker}")
                     st.rerun()
                else:
                     st.warning("Stock already exists.")
        
        st.markdown("---")
        st.write("⚡ Quick Actions")
        if st.button("📥 Import Top 100 Stocks"):
            import tickers_loader
            count = tickers_loader.update_master_stocks()
            st.success(f"Successfully imported {count} stocks (Kompas100 + Popular)!")
            st.rerun()
    
    # List & Delete
    with col_list:
        all_tickers = db.get_all_tickers()
        st.write(f"Total Monitored: **{len(all_tickers)}** stocks")
        
        with st.expander("View Request List"):
             st.text(", ".join(all_tickers))
        
        t_remove = st.selectbox("Remove from Watchlist", all_tickers)
        if st.button("Remove Ticker"):
            db.delete_master_stock(t_remove)
            st.warning(f"Removed {t_remove}")
            st.rerun()
