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
# Not: Bu liste zamanla eskiyebilir. Gerçek bir projede rotasyon servisi kullanılmalı.
# Binance Global'e ABD'den (Streamlit Cloud) erişim için public proxy listesi
# Masaüstü modunda boş bırakıyoruz (Direkt bağlantı)
PROXIES = ['']

# Global değişkenler
PREFERRED_PROXY = None
FORCE_SPOT_MODE = False
FORCE_MANUAL_MARKETS = False 

def inject_manual_markets(exchange):
    # Masaüstü modunda devre dışı
    return exchange

def get_exchange(use_spot=False, ignore_sticky=False):
    # Masaüstü Modu: Direkt ve Hızlı Bağlantı
    # options: defaultType: future vs spot
    default_type = 'spot' if use_spot else 'future'
    
    config = {
        'enableRateLimit': True,
        'options': {'defaultType': default_type},
        'timeout': 10000
    }
    
    return ccxt.binance(config)

def fetch_binance_ohlcv(symbol: str = 'BTC/USDT', timeframe: str = '1h', limit: int = 500) -> tuple[Optional[pd.DataFrame], str]:
    try:
        exchange = get_exchange(use_spot=False) # Masaüstünde direkt Futures
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        if not ohlcv: 
            return None, "Boş Veri"

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df, ""
        
    except Exception as e:
        return None, str(e)

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
    """
    # Eğer Manual Market Modu aktifse, API'den liste çekmeye çalışma (Hata verir)
    if FORCE_MANUAL_MARKETS:
        # data_loader içinde tanımlı hardcoded liste
        symbols = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 
            'DOGE/USDT', 'AVAX/USDT', 'TRX/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 
            'UNI/USDT', 'LTC/USDT', 'BCH/USDT', 'ATOM/USDT', 'XLM/USDT', 'ETC/USDT', 
            'FIL/USDT', 'XMR/USDT', 'NEAR/USDT', 'APT/USDT', 'QNT/USDT', 'LDO/USDT', 
            'HBAR/USDT', 'ICP/USDT', 'GRT/USDT', 'SAND/USDT', 'EOS/USDT', 'MANA/USDT'
        ]
        return [{'symbol': s} for s in symbols][:limit]

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
