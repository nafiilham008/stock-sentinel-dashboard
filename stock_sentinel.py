import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import database_manager as db
import data_engine as de
import analysis_engine as ae
import chart_engine as ce
import telegram_bot as bot

# --- Page Config ---
st.set_page_config(page_title="Stock Sentinel Dashboard", page_icon="📈", layout="wide")

# --- Auto-Refresh ---
# Refresh every 15 minutes (900,000 milliseconds)
count = st_autorefresh(interval=900000, limit=100, key="fizzbuzzcounter")

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
    st.session_state['new_scan_done'] = True
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
    
    # --- MACRO MARKET COMPASS ---
    macro = ae.get_macro_weather()
    if macro:
        if macro['color'] == 'green':
            st.success(f"**Cuaca IHSG Hari Ini: {macro['status']} ({macro['change_pct']:.2f}%)**\n\n{macro['advice']}")
        elif macro['color'] == 'red':
            st.error(f"**Cuaca IHSG Hari Ini: {macro['status']} ({macro['change_pct']:.2f}%)**\n\n{macro['advice']}")
        else:
            st.info(f"**Cuaca IHSG Hari Ini: {macro['status']} ({macro['change_pct']:.2f}%)**\n\n{macro['advice']}")
    
    st.markdown("---")
    
    # Auto-run scanner if empty (First load)
    if st.session_state['scan_results'].empty:
        st.info("🔄 Menjalankan Auto-Scan pertama kali... Mohon tunggu sebentar.")
        run_scanner()
        st.rerun()
    else:
        df_res = st.session_state['scan_results']
        send_tele = st.session_state.get('new_scan_done', False)
        tele_msg = ""
        if send_tele:
            phase_name, _ = ae.get_market_phase()
            tele_msg += f"🛡️ **Stock Sentinel Live Update ({phase_name})**\n\n"
        
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
            st.markdown("#### 🚀 Calon To The Moon (Breakout ATH)")
            st.caption("Saham yang harganya sudah sangat dekat dengan rekor harga tertinggi sepanjang masa (All-Time High).")
            df_ath = df_res[df_res['ath_distance_pct'] > -10].sort_values('ath_distance_pct', ascending=False).head(5)
            if not df_ath.empty:
                for _, row in df_ath.iterrows():
                    price = row['current_price']
                    ath = row['ath_price']
                    roe = row.get('roe', None)
                    tp_price = ath * 1.10 # Target 10%
                    cl_price = ath * 0.95 # Cutloss 5%

                    roe_text = "N/A"
                    if roe is not None:
                        roe_pct = roe * 100
                        if roe_pct >= 15:
                            roe_text = f"✅ {roe_pct:.2f}% (Sangat Sehat)"
                        elif roe_pct < 0:
                            roe_text = f"❌ {roe_pct:.2f}% (Rugi/Bakar Duit)"
                        else:
                            roe_text = f"⚠️ {roe_pct:.2f}% (Biasa/Kurang Sehat)"

                    with st.expander(f"⭐ {row['ticker']} (Jarak ke puncak: {row['ath_distance_pct']:.2f}%)"):
                        st.markdown(f"**Harga Saat Ini:** Rp {price:,.0f}")
                        st.markdown(f"**Target Puncak (ATH):** Rp {ath:,.0f}")
                        st.markdown(f"**Kesehatan Bisnis (ROE):** {roe_text}")
                        st.markdown("---")
                        st.markdown("💡 **Trading Playbook (AI Professional Advice):**")
                        
                        phase_name, phase_desc = ae.get_market_phase()
                        
                        # --- DYNAMIC NARRATIVE ENGINE (BREAKOUT) ---
                        narrative = ""
                        if "Golden Time" in phase_name or "Tutup" in phase_name or "Pre-Closing" in phase_name:
                            if price >= ath:
                                status_alert = st.success
                                status_msg = f"🎯 **KEPUTUSAN SAAT INI ({phase_name}):**\n\nHarga bertahan kuat di atas Rp {ath:,.0f} menjelang penutupan. **Sinyal Beli (Buy) Sangat Valid!** Hajar Kanan sekarang atau hold jika sudah punya."
                                narrative = f"Breakout terkonfirmasi sempurna di penghujung hari! Ini adalah 'Golden Time' yang kita tunggu. Penutupan yang kuat di atas resisten kritis menandakan institusi bersedia menahan barang (akumulasi), memberikan peluang besar harga akan lanjut reli besok pagi."
                            else:
                                status_alert = st.error
                                status_msg = f"🛑 **KEPUTUSAN SAAT INI ({phase_name}):**\n\nSangat disayangkan, harga gagal bertahan di atas Rp {ath:,.0f} dan bursa mau tutup. **Breakout Gagal.** Lupakan saham ini atau segera Cut Loss jika terlanjur beli."
                                narrative = f"Sayang sekali, saham ini gagal mempertahankan level penembusannya hingga bursa tutup. Pola seperti ini sering disebut 'False Breakout' (Jebakan Bull Trap). Bandar memancing ritel di pagi hari lalu membantingnya ke bawah. Hindari masuk."
                        elif "Pagi" in phase_name or "Pembukaan" in phase_name:
                            if price >= ath:
                                status_alert = st.info
                                status_msg = f"⏳ **KEPUTUSAN SAAT INI ({phase_name}):**\n\nHarga menembus Rp {ath:,.0f}, TAPI ini masih terlalu pagi. Rawan *profit taking*. Cicil beli kecil (Tes Ombak)."
                                narrative = f"Saham ini sedang berusaha menembus rekor harga tertinggi (ATH). Karena ini masih pagi, volatilitas sangat tinggi. Seringkali bandar sengaja menarik harga ke atas sesaat untuk memancing ritel sebelum dibanting. Tetap waspada, amati apakah antrean beli (bid) cukup tebal."
                            else:
                                status_alert = st.warning
                                status_msg = f"⏳ **KEPUTUSAN SAAT INI ({phase_name}):**\n\nBelum kuat menembus Rp {ath:,.0f}. Santai dulu, amati dari luar. Jangan tangkap pisau jatuh di pagi hari."
                                narrative = f"Saham ini berpotensi breakout, namun pagi ini masih terlihat ragu-ragu dan belum mampu menembus resisten kuatnya. Jangan buru-buru masuk, biarkan market membentuk arahnya terlebih dahulu hingga sesi siang."
                        else: # Sesi 1 or Sesi 2
                            if price >= ath:
                                status_alert = st.success
                                status_msg = f"👍 **KEPUTUSAN SAAT INI ({phase_name}):**\n\nTren terlihat positif siang ini. Harga konsisten di atas batas aman. Boleh tambah porsi beli (Average Up)."
                                narrative = f"Luar biasa! Melewati sesi pagi yang bergejolak, saham ini berhasil bertahan di atas harga ATH-nya. Ini adalah konfirmasi validasi tren positif. Bandar tampaknya serius melakukan akumulasi. Momentum sangat mendukung untuk masuk."
                            else:
                                status_alert = st.warning
                                status_msg = f"⏳ **KEPUTUSAN SAAT INI ({phase_name}):**\n\nHarga masih tertahan di bawah Rp {ath:,.0f}. Momentum mulai hilang. Wait and see sampai Golden Time (14:30) nanti."
                                narrative = f"Upaya penembusan harga tertinggi tampaknya tertahan di sesi ini. Harga tidak mampu dipertahankan dan tertekan kembali ke bawah resisten. Jangan memaksakan diri, lebih baik tunggu konfirmasi di jam 14:40 nanti."
                        
                        status_alert(status_msg)
                        
                        if macro and macro['color'] == 'red':
                            st.markdown(f"🚨 **PERINGATAN MACRO:** Walaupun saham ini punya potensi Breakout, **Cuaca IHSG sedang Badai**. Mayoritas saham *breakout* di saat market hancur berpotensi menjadi *Bull Trap* (Jebakan). Kurangi porsi beli atau *wait and see*.")
                        elif macro and macro['color'] == 'green':
                            st.markdown(f"🔥 **DUKUNGAN MACRO:** Cuaca IHSG sedang Euforia! Probabilitas *breakout* sukses jauh lebih tinggi. Angin sedang bertiup dari belakang layar.")
                            
                        # --- DYNAMIC PROJECTION ENGINE (BREAKOUT) ---
                        proyeksi = ""
                        if "Pagi" in phase_name or "Pembukaan" in phase_name:
                            proyeksi = f"- **Menjelang Siang (10:00 - 11:30):** Pantau apakah harga mampu bertahan di atas Rp {ath:,.0f}. Jika tiba-tiba melorot, lupakan dulu.\n- **Sesi Sore (14:40):** Ini waktu penentuan. Jika harga masih kuat bertengger di atas ATH, baru eksekusi beli dengan mantap."
                        elif "Sesi" in phase_name:
                            proyeksi = f"- **Sesi 2 (13:30 - 14:30):** Perhatikan apakah ada 'bantingan' (penurunan paksa) oleh bandar. Tetap santai.\n- **Jelang Tutup (14:40):** Keputusan final ada di jam ini. Jika *breakout* tetap valid, silakan tahan barangmu."
                        elif "Golden Time" in phase_name or "Tutup" in phase_name or "Pre-Closing" in phase_name:
                            proyeksi = f"- **Penutupan Hari Ini:** Evaluasi apakah saham ditutup kokoh. Jika ya, *breakout* sukses.\n- **Skenario Besok Pagi:** Rawan *profit taking* kilat. Siapkan antrean jual di target Rp {tp_price:,.0f}."
                        else:
                            proyeksi = f"- **Besok Pagi (09:00 - 09:30):** Waspada lonjakan atau bantingan di awal pembukaan.\n- **Siang (11:00):** Waktu untuk memastikan apakah tren kemarin masih berlanjut."

                        st.markdown(f"**Analisa Eksekusi AI:**\n{narrative}")
                        st.markdown(f"**Langkah Selanjutnya (Proyeksi Waktu):**\n{proyeksi}")
                        
                        bpjs_advice = ""
                        if "Pagi" in phase_name or "Pembukaan" in phase_name:
                            bpjs_advice = f"- **Strategi BPJS (Beli Pagi Jual Sore):** Kalau masuk sekarang niat main cepat, target jualmu di rentang **Rp {price * 1.02:,.0f} - Rp {price * 1.03:,.0f}** (+2-3%). JUAL sebelum bursa tutup berapapun harganya. Jangan ngarep besok mantul."
                        elif "Sesi" in phase_name:
                            bpjs_advice = f"- **Strategi BPJS (Beli Pagi Jual Sore):** Jika sudah mencapai batas cuan BPJS (sekitar **Rp {price * 1.02:,.0f}**), boleh langsung bungkus. Jangan terlalu serakah menunggu harga puncak."
                        else:
                            bpjs_advice = f"- **Strategi BPJS (Beli Pagi Jual Sore):** Sesi *Day Trading* sudah berakhir. Masuk jam segini otomatis kamu berhaluan Swing Trader (siap menahan barang menginap)."

                        st.markdown("---")
                        st.markdown("💸 **Exit Plan (Strategi Jual):**")
                        st.markdown(f"- **Take Profit:** Pasang **Auto Order Jual** di target **Rp {tp_price:,.0f}** (+10%).")
                        st.markdown(f"- **Cut Loss:** Sabuk pengaman di **Rp {cl_price:,.0f}**. Patuhi ketat.")
                        st.markdown(bpjs_advice)
                        
                        if send_tele:
                            tele_msg += f"🚀 *{row['ticker']}* (Rp {price:,.0f})\n{narrative}\n\n"
            else:
                st.info("Belum ada saham yang mau Breakout hari ini.")

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
            st.markdown("#### ⚡ Ada Pergerakan Bandar (Volatilitas Tinggi)")
            st.caption("Saham yang tiba-tiba ramai dibeli/dijual dengan volume tidak wajar hari ini.")
            df_vol = df_res[df_res['is_volatile'] == True].head(5)
            if not df_vol.empty:
                for _, row in df_vol.iterrows():
                    price = row['current_price']
                    change = row['price_change_pct']
                    vol = row['vol_spike_ratio']
                    roe = row.get('roe', None)
                    
                    roe_text = "N/A"
                    if roe is not None:
                        roe_pct = roe * 100
                        if roe_pct >= 15:
                            roe_text = f"✅ {roe_pct:.2f}% (Sangat Sehat)"
                        elif roe_pct < 0:
                            roe_text = f"❌ {roe_pct:.2f}% (Rugi/Bakar Duit)"
                        else:
                            roe_text = f"⚠️ {roe_pct:.2f}% (Biasa/Kurang Sehat)"
                    
                    if change > 0:
                        tp_low = price * 1.05
                        tp_high = price * 1.10
                        cl_price = price * 0.95

                        status_harga = f"📈 **NAIK** {change:.2f}%"
                        analisa = f"Volume transaksi meledak hingga {vol:.1f}x lipat rata-rata saat harga sedang NAIK. Secara teknikal, ini adalah jejak rekam bahwa Institusi/Bandar besar sedang melakukan akumulasi (borong barang)."
                        if roe is not None and roe < 0:
                            analisa += " **Namun PERHATIAN EKSTRA:** Secara fundamental, perusahaan ini mencetak kerugian (ROE Minus). Kenaikan ini berisiko tinggi murni karena spekulasi/gorengan. Disiplin *trading* harus ekstra ketat!"
                    else:
                        status_harga = f"📉 **TURUN** {abs(change):.2f}%"
                        analisa = f"Lampu Kuning Menyala! Terdapat ledakan volume {vol:.1f}x lipat diiringi harga yang TURUN. Ini mengindikasikan Distribusi (Bandar sedang buang barang masif ke pasar ritel)."

                    with st.expander(f"🔥 {row['ticker']} (Volume meledak {vol:.1f}x lipat)"):
                        st.markdown(f"**Harga Saat Ini:** Rp {price:,.0f}")
                        st.markdown(f"**Kondisi Hari Ini:** {status_harga}")
                        st.markdown(f"**Kesehatan Bisnis (ROE):** {roe_text}")
                        st.markdown("---")
                        st.markdown("💡 **Trading Playbook (AI Professional Advice):**")
                        st.markdown(f"**Insight Analis Dasar:** {analisa}")
                        st.markdown("---")
                        
                        phase_name, phase_desc = ae.get_market_phase()
                        
                        # --- DYNAMIC NARRATIVE ENGINE (VOLATILE) ---
                        if change > 0:
                            narrative = ""
                            if "Golden Time" in phase_name or "Tutup" in phase_name or "Pre-Closing" in phase_name:
                                if price >= cl_price:
                                    status_alert = st.success
                                    status_msg = f"🎯 **KEPUTUSAN SAAT INI ({phase_name}):**\n\nHarga ditutup aman di atas batas *cut loss* (Rp {cl_price:,.0f}). Tren akumulasi bandar **VALID**. Aman di-Hold."
                                    narrative = f"Pergerakan harga sukses dipertahankan hingga menjelang penutupan. Secara probabilitas, tren kenaikan (uptrend) jangka pendek masih sangat valid. Tidak ada tanda-tanda distribusi masif dari institusi."
                                else:
                                    status_alert = st.error
                                    status_msg = f"🛑 **KEPUTUSAN SAAT INI ({phase_name}):**\n\nBencana! Harga dijebol ke bawah Rp {cl_price:,.0f} menjelang tutup. Bandar distribusi diam-diam. **EKSEKUSI CUT LOSS!**"
                                    narrative = f"Lampu merah! Harga justru ditutup nyungsep menembus batas toleransi dukungan. Ini menandakan ledakan volume kemarin kemungkinan besar adalah aksi jualan terselubung bandar ke ritel. Sangat berisiko tinggi."
                            elif "Pagi" in phase_name or "Pembukaan" in phase_name:
                                if price >= cl_price * 1.05:
                                    status_alert = st.warning
                                    status_msg = f"⏳ **KEPUTUSAN SAAT INI ({phase_name}):**\n\nHarga melesat sangat kencang. Awas pancingan (FOMO)!"
                                    narrative = f"Volume ledakan kemarin berlanjut dengan euforia pagi ini, harga melesat kencang. Hati-hati FOMO (Fear of Missing Out). Seringkali harga ditarik kencang di awal hanya untuk jualan. Jangan kejar harga atas."
                                else:
                                    status_alert = st.info
                                    status_msg = f"⏳ **KEPUTUSAN SAAT INI ({phase_name}):**\n\nPagi ini rawan gocekan karena kemarin naik kencang. Jangan panik kalau tiba-tiba merah. Tahan diri dulu."
                                    narrative = f"Sangat wajar jika pagi ini harga bergerak volatil atau bahkan terkoreksi sedikit (Profit Taking wajar). Bandar sedang menguji apakah ada kepanikan ritel. Amati reaksinya hingga lewat jam 10:00."
                            else: # Sesi 1 or Sesi 2
                                if price > cl_price * 1.02:
                                    status_alert = st.success
                                    status_msg = f"👍 **KEPUTUSAN SAAT INI ({phase_name}):**\n\nTren naik terkonfirmasi siang ini! Bandar melanjutkan *Markup*. Boleh ikut antre beli (Hajar Kanan)."
                                    narrative = f"Konfirmasi yang solid! Setelah sempat diuji pagi tadi, harga kini stabil di area positif. Ini indikasi kuat bahwa 'Markup' (pengangkatan harga) oleh Institusi masih terus berlanjut. Momentum sangat baik."
                                else:
                                    status_alert = st.warning
                                    status_msg = f"⏳ **KEPUTUSAN SAAT INI ({phase_name}):**\n\nHarga tertahan. Hati-hati bandar sedang mengukur minat ritel. Jangan tambah muatan dulu."
                                    narrative = f"Harga terlihat loyo dan tertahan di sesi siang ini, padahal volume kemarin sangat besar. Ini bisa menjadi sinyal awal bandar mulai mendistribusikan (jual pelan-pelan) barangnya saat ritel sedang lengah."
                            
                            status_alert(status_msg)
                            
                            # --- DYNAMIC PROJECTION ENGINE (VOLATILE) ---
                            proyeksi = ""
                            if "Pagi" in phase_name or "Pembukaan" in phase_name:
                                if price > cl_price * 1.05:
                                    proyeksi = f"- **Menjelang Siang (10:30):** Karena pagi ini melesat naik, rawan dibanting siang nanti. Jangan buru-buru antre beli.\n- **Sore Hari (14:40):** Lihat apakah kenaikan pagi tadi sungguhan atau cuma jebakan."
                                else:
                                    proyeksi = f"- **Sesi Siang (11:00):** Jika pagi ini merah, pantau apakah jam 11 nanti mulai ditarik hijau. Jika ditarik hijau, itu adalah momen beli terbaik (Markup konfirmasi).\n- **Batas Waktu (14:40):** Jika sampai sore tetap tidak bisa naik, coret dari daftar."
                            elif "Sesi" in phase_name:
                                proyeksi = f"- **Sesi 2 (13:30 - 14:30):** Biasanya bandar mulai bergerak masif di jam ini. Waspadai volatilitas mendadak.\n- **Jelang Tutup (14:40):** Evaluasi akhir sebelum penutupan. Pastikan harga aman di atas batas *cut loss* (Rp {cl_price:,.0f})."
                            else:
                                proyeksi = f"- **Skenario Besok Pagi:** Jangan kaget jika pagi hari langsung merah sekejap (gocekan bandar). Jangan panik.\n- **Evaluasi Besok Siang:** Biarkan market menentukan arah aslinya setelah jam 10 pagi."

                            st.markdown(f"**Analisa Eksekusi AI:**\n{narrative}")
                            st.markdown(f"**Langkah Selanjutnya (Proyeksi Waktu):**\n{proyeksi}")
                            
                            bpjs_advice = ""
                            if "Pagi" in phase_name or "Pembukaan" in phase_name:
                                if price > cl_price * 1.05:
                                    bpjs_advice = f"- **Strategi BPJS (Beli Pagi Jual Sore):** Sangat disarankan untuk volatilitas liar! Target copet kilat di **Rp {price * 1.03:,.0f}** (+3%). Langsung hajar kiri (jual). Jangan bawa menginap."
                                else:
                                    bpjs_advice = f"- **Strategi BPJS (Beli Pagi Jual Sore):** Ladang emas pencopet. Masuk dekat *support* (**Rp {cl_price:,.0f}**), ambil cuan di **Rp {price * 1.03:,.0f}** lalu lari. Jangan terbawa perasaan jika sore dibanting."
                            elif "Sesi" in phase_name:
                                bpjs_advice = f"- **Strategi BPJS (Beli Pagi Jual Sore):** Jika sudah cuan lumayan sejak pagi (harga sudah menyentuh **Rp {price * 1.02:,.0f}**), amankan sekarang. Bandar sering buang barang di sesi siang/sore."
                            else:
                                bpjs_advice = f"- **Strategi BPJS (Beli Pagi Jual Sore):** Jam segini bukan waktu untuk copet harian. Pasang incaran eksekusi di **Rp {price * 1.02:,.0f}** untuk trading plan besok pagi saja."

                            st.markdown("---")
                            st.markdown("💸 **Exit Plan (Strategi Jual):**")
                            st.markdown(f"- **Take Profit:** Volatilitas tinggi = pergerakan cepat. Pasang antrean **Auto Order Jual** di rentang **Rp {tp_low:,.0f} - Rp {tp_high:,.0f}**.")
                            st.markdown(f"- **Cut Loss:** Sabuk pengaman di **Rp {cl_price:,.0f}**. Patuhi *cut loss*.")
                            st.markdown(bpjs_advice)
                            
                            if send_tele:
                                tele_msg += f"🔥 *{row['ticker']}* (Rp {price:,.0f})\n{narrative}\n\n"
                        else:
                            st.error(f"🛑 **Skenario Eksekusi:** Sangat berisiko tinggi (*High Risk*). Secara teknikal, membeli saham yang sedang didistribusi bandar sama dengan menangkap pisau jatuh. **Wait and See**.")
                            if send_tele:
                                tele_msg += f"🚨 *{row['ticker']}* (Rp {price:,.0f})\nDistribusi Bandar. Jauhi saham ini!\n\n"
            else:
                st.info("Pasar sedang sepi, tidak ada pergerakan mencolok.")

        if send_tele and tele_msg != "":
            bot.send_telegram_message(tele_msg)
            st.session_state['new_scan_done'] = False

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
