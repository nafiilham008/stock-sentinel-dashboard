# 🛡️ Stock Sentinel Dashboard

**Stock Sentinel** adalah asisten *trading* pintar dan *auto-scanner* khusus untuk saham-saham di Bursa Efek Indonesia (IHSG). Dibangun dengan Streamlit dan Python, aplikasi ini bertindak layaknya analis profesional pribadi yang memantau pergerakan pasar, mendeteksi sinyal penting, dan memberikan *advice* eksekusi yang adaptif terhadap kondisi *market* secara *real-time*.

## ✨ Fitur Utama (Features)

1. **🚀 Breakout & Volatility Scanner**
   *   **Breakout ATH:** Mendeteksi saham-saham yang harganya hampir menyentuh atau berhasil menembus rekor harga tertinggi sepanjang masa (*All-Time High*).
   *   **Volatility Alert:** Melacak ledakan volume yang tidak wajar (akumulasi/distribusi) secara seketika (*real-time*).

2. **🧠 AI Professional Playbook (Dynamic Narrative Engine)**
   Bukan sekadar *template* kaku. Aplikasi ini membaca cuaca IHSG (Macro) dan fase jam perdagangan (Pre-Market, Sesi 1, Golden Time, dll) untuk menghasilkan narasi analisa yang sangat peka terhadap konteks (*Context-Aware*).

3. **💸 Strategi BPJS (Beli Pagi Jual Sore) & Nominal Target**
   Sistem secara otomatis menghitung *Take Profit* dan *Cut Loss*, serta memberikan target nominal spesifik (rentang harga pasti) bagi *Day Trader* / *Scalper* tanpa perlu menghitung persentase secara manual.

4. **📈 Smart Signals & Candlestick Radar**
   *   **RSI Oversold:** Mencari saham-saham diskon tinggi (Jenuh Jual).
   *   **MACD Golden Cross:** Mendeteksi potensi awal *Reversal* (Perubahan tren naik).
   *   **Candlestick Detector:** Mendeteksi formasi *Hammer* (tanda pantulan) dan *Doji* (keraguan pasar).

5. **📊 Interactive Charting (Plotly)**
   Visualisasi pergerakan harga dengan *Candlestick*, indikator *Moving Average* (MA5 & MA20), dan injeksi **Radar Momentum Buy** berbentuk sinyal visual langsung di atas grafik saat harga menembus MA5 dengan kuat.

6. **📲 Telegram Live Alerts**
   Setiap kali proses *scan* selesai, Sentinel akan merangkum seluruh hasil observasi (lengkap dengan narasi AI) dan mengirimkannya langsung ke *smartphone* Anda melalui bot Telegram.

## 🛠️ Instalasi & Persiapan

1. Pastikan Anda sudah menginstal Python (disarankan versi 3.9 ke atas).
2. *Clone repository* ini:
   ```bash
   git clone https://github.com/nafiilham008/stock-sentinel-dashboard.git
   cd stock-sentinel-dashboard
   ```
3. Instal semua paket yang dibutuhkan (*dependencies*):
   ```bash
   pip install -r requirements.txt
   ```
4. (Opsional tapi Penting) Untuk mengaktifkan Notifikasi Telegram:
   * Buat bot baru di Telegram melalui **BotFather**.
   * Dapatkan *Token* bot.
   * Dapatkan *Chat ID* Anda (Bisa menjalankan skrip `python get_chat_id.py`).
   * Masukkan *Token* dan *Chat ID* di menu "Settings" dalam aplikasi *dashboard*.

## 🚀 Cara Menjalankan Aplikasi

Anda dapat menggunakan *batch script* yang sudah disediakan (untuk Windows):
```bash
run_dashboard.bat
```

Atau jalankan langsung melalui Streamlit:
```bash
streamlit run stock_sentinel.py
```

Dashboard akan otomatis terbuka di *browser* Anda (biasanya di `http://localhost:8501`).

## 💡 Best Practices

*   Biarkan aplikasi berjalan (jangan di- *close* tab-nya) selama jam bursa. Aplikasi dirancang untuk me-*refresh* dan *auto-scan* secara periodik.
*   *Advice* AI akan berubah-ubah sesuai jam, jadi pastikan Anda membacanya sebelum mengeksekusi pembelian.
*   Gunakan fitur integrasi Telegram jika Anda sering *mobile* dan tidak bisa melihat layar PC terus-menerus.

---
*Disclaimer: Seluruh data, analisa, dan notifikasi yang diberikan oleh Stock Sentinel hanya bersifat sebagai alat bantu riset (Assist). Keputusan beli/jual (Trading) sepenuhnya merupakan risiko dan tanggung jawab pengguna.*
