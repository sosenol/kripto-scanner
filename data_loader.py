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
PROXIES = [
    '', 
    'http://8.219.97.248:80',
    'http://20.206.106.192:80', 
    'http://162.223.94.164:80',
    'http://51.159.115.233:3128',
    'http://159.203.87.130:3128',
    'http://134.209.29.120:8080',
    'http://167.71.5.176:8080',
    'http://165.22.216.59:8080',
    'http://138.197.148.215:80',
    'http://20.210.113.32:80',
    'http://51.158.154.173:3128',
    'http://51.158.147.227:3128',
    'http://188.166.216.208:80',
    'http://64.225.4.29:80',
    'http://159.89.49.172:80',
    'http://165.227.215.71:80',
    'http://206.189.135.195:80',
    'http://142.93.57.37:80',
    'http://167.99.197.106:80',
    'http://157.230.252.176:80',
    'http://104.248.83.212:80',
    'http://134.209.106.220:80',
    'http://68.183.134.58:80',
    'http://167.71.168.194:80'
]

import random
random.shuffle(PROXIES) # Her yüklemede listeyi karıştır

# Global değişkenler
PREFERRED_PROXY = None
FORCE_SPOT_MODE = False
FORCE_MANUAL_MARKETS = True # exchangeInfo datasını çekmeyip elle tanımlayacağız

def inject_manual_markets(exchange):
    """
    Binance'in exchangeInfo endpoint'i engellendiği için
    en popüler coinleri elle tanımlıyoruz. Bu sayede load_markets() çağrısından kurtuluyoruz.
    """
    markets = {}
    ids = {}
    
    # En popüler 30 Coin
    symbols = [
        'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 
        'DOGE/USDT', 'AVAX/USDT', 'TRX/USDT', 'DOT/USDT', 'MATIC/USDT', 'LINK/USDT', 
        'UNI/USDT', 'LTC/USDT', 'BCH/USDT', 'ATOM/USDT', 'XLM/USDT', 'ETC/USDT', 
        'FIL/USDT', 'XMR/USDT', 'NEAR/USDT', 'APT/USDT', 'QNT/USDT', 'LDO/USDT', 
        'HBAR/USDT', 'ICP/USDT', 'GRT/USDT', 'SAND/USDT', 'EOS/USDT', 'MANA/USDT'
    ]
    
    for symbol in symbols:
        base, quote = symbol.split('/')
        market_id = base + quote # BTCUSDT
        markets[symbol] = {
            'id': market_id,
            'symbol': symbol,
            'base': base,
            'quote': quote,
            'baseId': base,
            'quoteId': quote,
            'active': True,
            'precision': {'amount': 8, 'price': 8},
            'limits': {'amount': {'min': 0.00001, 'max': 9000}, 'cost': {'min': 5, 'max': 1000000}},
            'info': {}
        }
        ids[market_id] = markets[symbol]
        
    exchange.markets = markets
    exchange.markets_by_id = ids
    exchange.options['adjustForTimeDifference'] = False # Time sync da yapma
    return exchange

def get_exchange(use_spot=False, ignore_sticky=False):
    import random
    
    # Global Zorlama veya Parametre
    use_spot = use_spot or FORCE_SPOT_MODE
    
    # options: defaultType: future vs spot
    default_type = 'spot' if use_spot else 'future'
    
    config = {
        'enableRateLimit': True,
        'options': {'defaultType': default_type},
        'timeout': 20000, 
        'verify': False 
    }
    
    # Proxy Seçimi
    if PREFERRED_PROXY is not None and not ignore_sticky:
        proxy = PREFERRED_PROXY
    else:
        proxy = random.choice(PROXIES)
    
    if proxy:
        config['proxies'] = {
            'http': proxy,
            'https': proxy
        }
    
    ex = ccxt.binance(config)
    
    if FORCE_MANUAL_MARKETS:
        ex = inject_manual_markets(ex)
        
    return ex

def fetch_binance_ohlcv(symbol: str = 'BTC/USDT', timeframe: str = '1h', limit: int = 500) -> tuple[Optional[pd.DataFrame], str]:
    # Dönüş formatı: (DataFrame, HataMesajı)
    
    max_retries = 4
    last_error = ""
    
    for i in range(max_retries):
        try:
            ignore_sticky = True if i > 0 else False
            use_spot = True if i >= 1 else False
            
            exchange = get_exchange(use_spot=use_spot, ignore_sticky=ignore_sticky)
            
            # User-Agent ve Referer (Bypass attempt)
            exchange.userAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            exchange.headers = {
                'Referer': 'https://www.binance.com/',
                'Origin': 'https://www.binance.com'
            }
            
            # load_markets() çağırmadan direkt fetch
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not ohlcv: 
                last_error = "Boş Veri"
                continue

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df, ""
            
        except Exception as e:
            last_error = str(e)
            continue
            
    return None, last_error

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
