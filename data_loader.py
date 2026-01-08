import ccxt
import pandas as pd
import re
from typing import Optional

# Whitelist (Majör Coinler)
MAJOR_COINS = {
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "AVAX", "DOGE", "TRX", "DOT",
    "LINK", "MATIC", "LTC", "SHIB", "BCH", "UNI", "XLM", "ATOM", "XMR", "ETC",
    "HBAR", "FIL", "LDO", "APT", "VET", "MKR", "NEAR", "OP", "AAVE",
    "INJ", "GRT", "RNDR", "STX", "EGLD", "SAND", "THETA", "EOS", "IMX", "AXS",
    "MANA", "SNX", "ALGO", "FTM", "NEO", "FLOW", "XTZ", "KAVA", "MINA", "CHZ",
    "GALA", "APE", "IOTA", "ZEC", "CRV", "RUNE", "DYDX", "COMP", "ARB",
    "PEPE", "SUI", "SEI", "TIA", "ORDI", "BONK", "WLD", "FET", "AGIX",
    "GMX", "WOO", "JASMY", "ENS", "CFX", "BLUR", "FLOKI", "TON", "ICP",
    "1000SHIB", "1000PEPE", "1000FLOKI", "1000BONK", "GMT", "POL", "TAO",
    "JTO", "JUP", "PYTH", "W", "ENA", "NOT", "PEOPLE", "LUNC", "LUNA",
    "PENDLE", "STRK", "ZRO", "LISTA", "IO", "ZK", "BOME", "MEW", "ONDO"
}

# Binance Global'e ABD'den (Streamlit Cloud) erişim için public proxy listesi
PROXIES = [
    '', # Direkt bağlantı (Bazı sunucularda çalışabilir)
    'http://65.109.219.160:80',
    'http://20.206.106.192:80', 
    'http://162.223.94.164:80',
    'http://8.219.97.248:80',
    'http://20.210.113.32:80',
    'http://51.159.115.233:3128',
    'http://51.158.154.173:3128',
    'http://51.158.147.227:3128',
    'http://159.203.87.130:3128'
]

def get_exchange():
    # Streamlit Cloud (ABD) sunucularından Binance Global'e erişmek yasak.
    # Bu yüzden basit bir proxy rotasyonu deneyeceğiz.
    
    import random
    
    # options: defaultType: future
    config = {
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
        'timeout': 10000
    }
    
    # Rastgele bir proxy seç (yükü dağıtmak için)
    # Not: Gerçek bir üretim ortamında paralı/özel proxy kullanılmalı.
    proxy = random.choice(PROXIES)
    
    if proxy:
        config['proxies'] = {
            'http': proxy,
            'https': proxy
        }
        print(f"🔗 Proxy ile bağlanılıyor: {proxy}")
    
    return ccxt.binance(config)

def fetch_binance_ohlcv(symbol: str = 'BTC/USDT', timeframe: str = '1h', limit: int = 500) -> Optional[pd.DataFrame]:
    # Eğer ilk deneme başarısız olursa, farklı bir proxy ile tekrar dene (Basit Retry Mekanizması)
    max_retries = 3
    for _ in range(max_retries):
        try:
            exchange = get_exchange()
            # Bot korumasını aşmak için User-Agent
            exchange.userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv: return None
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"⚠️ Veri çekme hatası (Retry): {e}")
            continue # Sonraki döngüde farklı proxy ile dene
            
    return None

def fetch_open_interest(symbol: str) -> Optional[float]:
    try:
        exchange = get_exchange()
        ticker = exchange.fetch_open_interest(symbol)
        return float(ticker.get('openInterestAmount', 0)) 
    except:
        return None

def fetch_coins_by_mode(mode: str = "major", limit: int = 20, verbose: bool = True):
    """
    3 Farklı Tarama Modu:
    - "major": Whitelist'teki majör coinler
    - "volatility": Tüm piyasa, sadece volatiliteye göre
    - "risk": Shitcoinler (Whitelist dışı, hacimli)
    """
    try:
        exchange = get_exchange()
        tickers = exchange.fetch_tickers()
        
        BLACKLIST = ['USDC', 'TUSD', 'BUSD', 'FDUSD', 'DAI', 'USDP', 'EUR']
        
        candidates = []
        
        for symbol, ticker in tickers.items():
            if '/USDT' not in symbol: continue
            if '-' in symbol or '_' in symbol: continue
            
            base = symbol.split('/')[0]
            if base in BLACKLIST: continue
            
            volume = ticker.get('quoteVolume')
            if not volume: continue
            vol = float(volume)
            
            # Mod bazlı filtreleme
            if mode == "major":
                if base not in MAJOR_COINS: continue
                if vol < 10_000_000: continue  # 10M minimum
            elif mode == "volatility":
                if vol < 5_000_000: continue  # 5M minimum
            elif mode == "risk":
                if base in MAJOR_COINS: continue  # Majörler hariç
                if vol < 5_000_000: continue
            
            candidates.append({'symbol': symbol, 'volume': vol, 'base': base})
        
        if verbose:
            print(f"📊 {mode.upper()} modunda {len(candidates)} coin bulundu")
        
        # Volatilite hesabı
        volatile_coins = []
        
        for item in candidates[:100]:  # Max 100 coin tara
            sym = item['symbol']
            try:
                ohlcv = exchange.fetch_ohlcv(sym, timeframe='4h', limit=6)
                if not ohlcv or len(ohlcv) < 6: continue
                
                highs = [c[2] for c in ohlcv]
                lows = [c[3] for c in ohlcv]
                
                max_high = max(highs)
                min_low = min(lows)
                volatility = (max_high - min_low) / min_low * 100 if min_low > 0 else 0
                
                volatile_coins.append({
                    'symbol': sym,
                    'volatility': volatility,
                    'volume': item['volume'],
                    'base': item['base']
                })
            except:
                continue
        
        volatile_coins.sort(key=lambda x: x['volatility'], reverse=True)
        
        if verbose:
            print(f"🎯 En volatil {limit} coin seçildi!")
        
        return volatile_coins[:limit]

    except Exception as e:
        print(f"Hata: {e}")
        return [{'symbol': 'BTC/USDT', 'volatility': 0, 'volume': 0}]

# Eski fonksiyonla uyumluluk
def fetch_top_major_coins(limit=20, verbose=True):
    return fetch_coins_by_mode("major", limit, verbose)
