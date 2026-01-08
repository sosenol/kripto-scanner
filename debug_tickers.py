import ccxt
import json

try:
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    
    print("Fetching tickers...")
    tickers = exchange.fetch_tickers()
    print(f"Total tickers: {len(tickers)}")
    
    # Print first 5 keys to see format
    keys = list(tickers.keys())[:5]
    print(f"Sample keys: {keys}")
    
    # Check USDT pairs
    usdt_pairs = [k for k in tickers.keys() if 'USDT' in k]
    print(f"USDT pairs count: {len(usdt_pairs)}")
    print(f"Sample USDT pairs: {usdt_pairs[:5]}")
    
except Exception as e:
    print(f"Error: {e}")
