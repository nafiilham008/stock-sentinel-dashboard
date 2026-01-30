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

# Navigation for cleanup (Portfolio Manager moved to sidebar expander or kept as separate if too complex, 
# for now let's keep Portfolio Manager as a separate page optionally, or integrate it. 
# Plan said "Unified", so let's try to make it single page or minimal Nav)
# To keep it simple, I will keep 'Portfolio Manager' as a separate "Admin" page in sidebar, 
# but the main page is "Dashboard" (Unified).

page = st.sidebar.radio("Menu", ["Dashboard (Live)", "Portfolio Manager", "Settings"])

# --- MAIN PAGE: DASHBOARD (UNIFIED) ---
if page == "Dashboard (Live)":
    st.title("🛡️ Trading Station")
    
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
        
        # Split into 2 cols: Breakout & Volatile
        col_bo, col_vol = st.columns(2)
        
        with col_bo:
            st.markdown("#### 🚀 Potential Breakout (Near ATH)")
            df_ath = df_res[df_res['ath_distance_pct'] > -10].sort_values('ath_distance_pct', ascending=False).head(5)
            if not df_ath.empty:
                st.dataframe(
                    df_ath[['ticker', 'current_price', 'ath_distance_pct']]
                    .style.format({"current_price": "{:,.0f}", "ath_distance_pct": "{:.2f}%"}),
                    use_container_width=True,
                    height=150
                )
            else:
                st.caption("No breakouts detected.")

        with col_vol:
            st.markdown("#### ⚡ Volatility Alert")
            df_vol = df_res[df_res['is_volatile'] == True].head(5)
            if not df_vol.empty:
                st.dataframe(
                    df_vol[['ticker', 'current_price', 'vol_spike_ratio']]
                    .style.format({"current_price": "{:,.0f}", "vol_spike_ratio": "{:.1f}x"}),
                    use_container_width=True,
                    height=150
                )
            else:
                st.caption("Market is calm.")

    st.divider()

    # --- SECTION 2: CHARTS & PORTFOLIO (SPLIT) ---
    col_main, col_chart = st.columns([1, 1.5])

    with col_main:
        st.markdown("### 💼 My Portfolio")
        df_port = db.get_portfolio()
        
        if not df_port.empty:
            st.dataframe(
                df_port[['ticker', 'buy_price', 'notes']]
                .style.format({"buy_price": "Rp {:,.0f}"}),
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
    
    with st.form("settings"):
        t_in = st.text_input("Bot Token", current_token, type="password")
        c_in = st.text_input("Chat ID", current_chat_id)
        if st.form_submit_button("Save"):
            bot.setup_credentials(t_in, c_in)
            st.success("Saved.")
            
    if st.button("Test Alert"):
        bot.send_telegram_message("🔔 Test from Unified Dashboard.")
