import streamlit as st
import pandas as pd
from data_loader import fetch_binance_ohlcv, fetch_coins_by_mode
from analyzers import AIAnaliz

st.set_page_config(page_title="TERMINAL SCANNER", page_icon="💻", layout="wide")

st.markdown("""
<style>
    /* Global renk düzeltmeleri */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    /* Slider ve Selectbox etiketleri için beyaz renk zorla */
    label[data-testid="stWidgetLabel"] {
        color: #ffffff !important;
        font-weight: bold !important;
    }
    /* Expander arka planı */
    .st-emotion-cache-p5msec {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
    }
    .terminal-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        color: #c9d1d9;
    }
    .price-row {
        background: #0d1117;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .waiting-msg {
        text-align: center;
        padding: 50px;
        color: #8b949e;
        font-size: 18px;
    }
    /* Buton rengi */
    .stButton > button {
        background-color: #238636 !important;
        color: white !important;
        font-weight: bold;
        border: none;
    }
    .stButton > button:hover {
        background-color: #2ea043 !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='color: #ffffff; text-align: center;'>💻 TERMINAL SCANNER</h1>", unsafe_allow_html=True)

# === AYARLAR ===
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    scan_mode = st.selectbox("🎯 Tarama Modu", ["🛡️ Majör Coinler", "🔥 Yüksek Volatilite", "⚠️ Risk Avcısı"], index=0)
with col2:
    # Varsayılan kar hedefi düşürüldü (%0.5)
    min_profit = st.slider("💰 Min. Kar (%)", 0.1, 10.0, 0.5, 0.1)
with col3:
    # Varsayılan AI güveni düşürüldü (%50)
    min_ai = st.slider("🧠 Min. AI (%)", 40, 90, 50, 2)

mode_map = {"🛡️ Majör Coinler": "major", "🔥 Yüksek Volatilite": "volatility", "⚠️ Risk Avcısı": "risk"}

def clean_symbol(s):
    return s.split(':')[0] if ':' in s else s

def render_card(data):
    is_long = "LONG" in data.get('Yön', '')
    dir_class = "direction-long" if is_long else "direction-short"
    dir_text = "LONG" if is_long else "SHORT"
    
    win_rate = data.get('Win_Rate', 0)
    mtf_uyum = data.get('MTF_Uyum', False)
    
    # Kart sınıfı belirleme
    card_class = "terminal-card"
    if mtf_uyum:
        card_class += " card-strong"
    elif win_rate < 50 and win_rate > 0:
        card_class += " card-low-conf"
    
    badge = ""
    if mtf_uyum:
        badge = "<span class='strong-badge'>🎯 GÜÇLÜ</span>"
    elif win_rate < 50 and win_rate > 0:
        badge = "<span class='low-badge'>⚠️</span>"
    
    wr_color = "#69f0ae" if win_rate >= 50 else "#ff9800"
    
    return f"""
    <div class="{card_class}">
        <div class="card-header">
            <span class="coin-name">{data.get('Sembol', 'N/A')}{badge}</span>
            <span class="{dir_class}">{dir_text}</span>
        </div>
        <div class="price-row">
            <span class="price-entry">G: ${data.get('Fiyat', 0):.4f}</span>
            <span class="price-target">H: ${data.get('Hedef', 0):.4f}</span>
            <span class="price-stop">S: ${data.get('Stop', 0):.4f}</span>
        </div>
        <div class="stats-row">
            <span>AI: %{data.get('AI_Skor', 50):.0f}</span>
            <span>1D: {data.get('Trend_1D', '-')}</span>
            <span>{data.get('Likidite', '✅')}</span>
            <span class="profit-badge">%{data.get('Potansiyel', 0):.1f}</span>
        </div>
        <div class="stats-row">
            <span>MACD: {data.get('MACD', '-')}</span>
            <span>Ichi: {data.get('Ichimoku', '-')}</span>
            <span>Fund: {data.get('Funding', '-')[:6]}</span>
        </div>
        <div class="backtest-row">
            <span>⭐ WR: <b style="color:{wr_color}">%{win_rate:.0f}</b></span> | 
            <span>📊 {data.get('Trade_Count', 0)} işlem</span> | 
            <span>PF: {data.get('Profit_Factor', 0):.1f}</span>
        </div>
        <div style="font-size:9px;color:#555;margin-top:4px;">MTF: {data.get('MTF_Detay', '-')}</div>
    </div>
    """

if st.button("🔍 TARAMAYI BAŞLAT", use_container_width=True):
    status = st.empty()
    progress = st.progress(0)
    
    mode = mode_map[scan_mode]
    errors = []
    
    mode = mode_map[scan_mode]
    errors = []
    
    # Bağlantı testi (Retry Mekanizması ile)
    from data_loader import get_exchange
    connection_success = False
    last_error = ""
    
    with st.spinner("🌍 Binance sunucularına bağlanılıyor (Proxy deneniyor)..."):
        mask_cols = st.columns([1, 10]) # İkon ve yazı hizası için
        for attempt in range(1, 6): # 5 kere dene
            try:
                ex = get_exchange()
                ex.fetch_time() # Ping testi
                connection_success = True
                status.success(f"🟢 Binance Bağlantısı Başarılı (Deneme: {attempt})")
                break
            except Exception as e:
                last_error = str(e)
                # Hata olsa bile devam et, sonraki proxy'i dene
                continue
    
    if not connection_success:
        errors.append(f"❌ Binance API Bağlantı Hatası: Hiçbir proxy çalışmadı. Son Hata: {last_error}")
        status.error("🔴 API Bağlantı Sorunu - Sayfayı Yenileyin")
        with st.expander("Hata Detayları"):
            st.write(last_error)

    try:
        if connection_success:
            coins = fetch_coins_by_mode(mode, limit=30, verbose=False)
            if not coins:
                errors.append("⚠️ Mevcut modda (veya seçilen hacimde) taranacak coin bulunamadı.")
        else:
            coins = []
    except Exception as e:
        errors.append(f"❌ Tarama Hatası: {str(e)}")
        coins = []
    
    import concurrent.futures
    import time

    # Paralel Tarama Fonksiyonu
    def analyze_coin(item):
        symbol = item['symbol']
        clean_sym = clean_symbol(symbol)
        try:
            # Her thread kendi proxy bağlantısını kullanır
            df_1h = fetch_binance_ohlcv(symbol, timeframe='1h', limit=500)
            if df_1h is None: return {'symbol': clean_sym, 'status': 'rejected', 'reason': 'Veri Yok'}
            
            df_4h = fetch_binance_ohlcv(symbol, timeframe='4h', limit=100)
            df_15m = fetch_binance_ohlcv(symbol, timeframe='15m', limit=100)
            df_1d = fetch_binance_ohlcv(symbol, timeframe='1d', limit=30)
            
            ai_data = AIAnaliz.hesapla_olasilik(df_1h, df_1d, symbol, df_4h, df_15m)
            
            potansiyel = ai_data['Setup'].get('Potansiyel', 0)
            ai_skor = ai_data['AI_Skor']
            
            # Sonuç objesi
            result = {
                "Sembol": clean_sym,
                "Yön": ai_data['Tahmin'],
                "Fiyat": ai_data['Setup'].get('Giriş', 0),
                "Hedef": ai_data['Setup'].get('Hedef', 0),
                "Stop": ai_data['Setup'].get('Stop', 0),
                "Potansiyel": potansiyel,
                "AI_Skor": ai_skor,
                "Trend_1D": ai_data.get('Trend_1D', '-'),
                "Likidite": ai_data.get('Likidite', '✅'),
                "MACD": ai_data.get('MACD', '-'),
                "Ichimoku": ai_data.get('Ichimoku', '-'),
                "Funding": ai_data.get('Funding', '-'),
                "Win_Rate": ai_data.get('Win_Rate', 0),
                "Trade_Count": ai_data.get('Trade_Count', 0),
                "Profit_Factor": ai_data.get('Profit_Factor', 0),
                "MTF_Uyum": ai_data.get('MTF_Uyum', False),
                "MTF_Detay": ai_data.get('MTF_Detay', '-')
            }
            
            # Ön Eleme Kontrolü
            if potansiyel < min_profit:
                return {'symbol': clean_sym, 'status': 'rejected', 'reason': f'Düşük Kar: %{potansiyel:.2f}'}
            if ai_skor < min_ai:
                return {'symbol': clean_sym, 'status': 'rejected', 'reason': f'Düşük Güven: %{ai_skor}'}

            result['status'] = 'accepted'
            return result
        except Exception as e:
            return {'symbol': clean_sym, 'status': 'error', 'reason': str(e)}

    results = []
    rejected = []
    
    # Progress Bar ve Durum Metni
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Paralel İşlemi Başlat (Max 5 Thread - Proxy'i yormamak için)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(analyze_coin, coin): coin for coin in coins}
        
        completed = 0
        total = len(coins)
        
        for future in concurrent.futures.as_completed(futures):
            coin = futures[future]
            try:
                data = future.result()
                if data:
                    if data['status'] == 'accepted':
                        results.append(data)
                    elif data['status'] == 'rejected':
                        rejected.append(data)
            except Exception as exc:
                pass
            
            completed += 1
            progress_bar.progress(completed / total)
            status_text.markdown(f"⏳ Taranıyor: **{coin['symbol']}** ({completed}/{total}) - Bulunan: {len(results)}")
            
    status_text.empty()
    progress_bar.empty()
    
    elite = [r for r in results]
    
    # MTF uyumlu olanları öne, sonra potansiyele göre sırala
    elite.sort(key=lambda x: (-int(x['MTF_Uyum']), -x['Potansiyel']))
    
    if errors:
        for err in errors:
            st.warning(err)
            
    if elite:
        st.success(f"✅ {len(elite)} Fırsat Bulundu ({scan_mode})")
        
        for i in range(0, len(elite), 3):
            batch = elite[i:i+3]
            cols = st.columns(3)
            for j, data in enumerate(batch):
                with cols[j]:
                    st.markdown(render_card(data), unsafe_allow_html=True)
    
    # Fırsat bulunsa da bulunmasa da Reddedilenleri göster (Kullanıcı güveni için)
    if rejected:
        with st.expander(f"🚫 Filtreye Takılanlar ({len(rejected)} Coin)"):
            st.write("Aşağıdaki coinler tarandı ancak kar veya güven kriterlerinize uymadı:")
            rej_df = pd.DataFrame(rejected)[['symbol', 'reason']]
            st.dataframe(rej_df, hide_index=True)
            
    if not elite and not errors:
        st.markdown(f"""
        <div class="waiting-msg">
            📡 {scan_mode} modunda şu an uygun fırsat yok<br>
            <small>Filtreleri (Kar veya AI) gevşetmeyi dene</small>
        </div>
        """, unsafe_allow_html=True)
