import requests
import database_manager as db

def send_telegram_message(message):
    """
    Sends a message via Telegram Bot using credentials stored in DB.
    """
    token = db.get_setting("TELEGRAM_BOT_TOKEN")
    chat_id = db.get_setting("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Telegram credentials not found in DB.")
        return False, "Credentials missing"
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True, "Message sent"
        else:
            return False, f"Error: {response.text}"
    except Exception as e:
        return False, str(e)

def setup_credentials(token, chat_id):
    """
    Helper to save credentials to DB.
    """
    db.set_setting("TELEGRAM_BOT_TOKEN", token)
    db.set_setting("TELEGRAM_CHAT_ID", chat_id)
    print("Telegram credentials saved.")

def format_currency(value):
    return f"Rp {value:,.0f}"

def send_scan_report(title, df_results):
    """
    Formats a dataframe of scan results and sends it to Telegram.
    """
    if df_results.empty:
        return False, "No data to send"
        
    message = f"🛡️ **Stock Sentinel: {title}**\n\n"
    
    count = 0
    for index, row in df_results.iterrows():
        if count >= 10: # Limit to top 10 to avoid spamming/limit
            message += f"\n... and {len(df_results) - 10} more."
            break
            
        ticker = row['ticker']
        price = format_currency(row['current_price'])
        
        if 'ath_distance_pct' in row:
            # ATH Report
            dist = row['ath_distance_pct']
            icon = "🚀" if dist >= 0 else "📈"
            message += f"{icon} **{ticker}** @ {price}\n"
            message += f"   ATH Dist: {dist:.2f}%\n"
            
        elif 'vol_spike_ratio' in row:
            # Volatility Report
            vol = row['vol_spike_ratio']
            change = row['price_change_pct']
            icon = "⚡"
            message += f"{icon} **{ticker}** @ {price}\n"
            message += f"   Vol: {vol:.1f}x | Price: {change:+.2f}%\n"
        
        elif 'rsi' in row:
            # RSI Report
            rsi_val = row['rsi']
            message += f"📉 **{ticker}** @ {price}\n"
            message += f"   RSI: {rsi_val:.1f} (Oversold)\n"

        elif 'macd_val' in row:
             # MACD Report
             message += f"✨ **{ticker}** @ {price}\n"
             message += f"   Golden Cross Detected! (Bullish)\n"
        
        # --- Trade Suggestions ---
        if 'plan_cons_sl' in row:
            sl_c = format_currency(row['plan_cons_sl'])
            tp_c = format_currency(row['plan_cons_tp'])
            sl_a = format_currency(row['plan_aggr_sl'])
            tp_a = format_currency(row['plan_aggr_tp'])
            
            message += f"   🎯 **Plan A (Safe):** SL {sl_c} | TP {tp_c}\n"
            message += f"   🚀 **Plan B (Aggressive):** SL {sl_a} | TP {tp_a}\n"
            
        count += 1
        
    return send_telegram_message(message)
