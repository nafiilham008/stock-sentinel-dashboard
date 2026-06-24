import requests
import time

# Masukkan Token Bot Telegram Anda di sini untuk mencari Chat ID
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

def get_chat_id():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    print(f"Checking for messages on bot... ({url})")
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data['ok']:
            results = data['result']
            if not results:
                print("\n❌ Belum ada pesan masuk.")
                print("Tolong buka Bot Telegram kamu, klik START atau kirim pesan 'Halo'.")
                print("Lalu jalankan script ini lagi.")
                return None
            
            # Get the latest message
            latest_msg = results[-1]
            chat_id = latest_msg['message']['chat']['id']
            username = latest_msg['message']['chat'].get('username', 'Unknown')
            
            print(f"\n✅ BERHASIL! Ditemukan Chat ID.")
            print(f"👤 User: {username}")
            print(f"🆔 Chat ID: {chat_id}")
            print("-" * 30)
            print("Simpan Chat ID ini untuk setting dashboard.")
            return chat_id
        else:
            print("Error connecting to Telegram API.")
            print(data)
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    get_chat_id()
