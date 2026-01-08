from data_loader import get_top_50_coins

print("Testing get_top_50_coins()...")
coins = get_top_50_coins()
print(f"Coin Count: {len(coins)}")
print(f"First 5 Coins: {coins[:5]}")

if len(coins) > 0:
    print("SUCCESS: Coins fetched.")
else:
    print("FAILURE: Coin list is empty.")
