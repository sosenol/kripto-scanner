import streamlit as st
import pandas as pd
from data_loader import fetch_binance_ohlcv, fetch_coins_by_mode
from analyzers import AIAnaliz

st.set_page_config(page_title="TERMINAL SCANNER", page_icon="💻", layout="wide")

st.markdown("""
<style>
    /* Streamlit Cloud için arka planı zorla */
    .stApp {
        background-color: #0a0a0a !important;
    }
    .main { 
        background-color: #0a0a0a; 
    }
    div[data-testid="stExpander"] {
        background-color: #141414;
        border: 1px solid #2a2a2a;
    }
    .terminal-card { 
        background: #141414; 
        border: 1px solid #2a2a2a; 
        border-radius: 8px; 
        padding: 12px; 
        margin: 5px 0; 
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='color: #fff; text-align: center;'>💻 TERMINAL SCANNER</h1>", unsafe_allow_html=True)

# === AYARLAR ===
col1, col2, col3 = st.columns(3)
with col1:
    scan_mode = st.selectbox("🎯 Tarama Modu", ["🛡️ Majör Coinler", "🔥 Yüksek Volatilite", "⚠️ Risk Avcısı"])
with col2:
    min_profit = st.slider("💰 Min. Kar (%)", 0.5, 10.0, 1.5, 0.5)
with col3:
    min_ai = st.slider("🧠 Min. AI (%)", 50, 80, 52, 2)

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
    try:
        coins = fetch_coins_by_mode(mode, limit=30, verbose=False)
        if not coins:
            errors.append("API'den veri alınamadı. (Binance IP'nizi engellemiş olabilir)")
    except Exception as e:
        errors.append(f"Tarama hatası: {str(e)}")
        coins = []
    
    results = []
    
    for i, item in enumerate(coins):
        symbol = item['symbol']
        clean_sym = clean_symbol(symbol)
        
        try:
            df_1h = fetch_binance_ohlcv(symbol, timeframe='1h', limit=500)
            df_4h = fetch_binance_ohlcv(symbol, timeframe='4h', limit=100)
            df_15m = fetch_binance_ohlcv(symbol, timeframe='15m', limit=100)
            df_1d = fetch_binance_ohlcv(symbol, timeframe='1d', limit=30)
            
            if df_1h is None:
                continue # Bu coin için veri çekilemedi
                
            ai_data = AIAnaliz.hesapla_olasilik(df_1h, df_1d, symbol, df_4h, df_15m)
            
            potansiyel = ai_data['Setup'].get('Potansiyel', 0)
            ai_skor = ai_data['AI_Skor']
            
            results.append({
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
            })
        except:
            pass
            
        progress.progress((i + 1) / len(coins))
    
    status.empty()
    progress.empty()
    
    # Filtreleme
    elite = [r for r in results if r['Potansiyel'] >= min_profit and r['AI_Skor'] >= min_ai]
    
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
    elif not errors: # Hata yok ama fırsat da yok
        st.markdown(f"""
        <div class="waiting-msg">
            📡 {scan_mode} modunda şu an uygun fırsat yok<br>
            <small>Filtreleri (Kar veya AI) gevşetmeyi dene</small>
        </div>
        """, unsafe_allow_html=True)
