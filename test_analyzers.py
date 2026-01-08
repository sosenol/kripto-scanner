import pandas as pd
import pandas_ta as ta
import numpy as np
from analyzers import AIAnaliz

# Create dummy data
print("Creating dummy data...")
data = {
    'timestamp': pd.date_range(start='2024-01-01', periods=200, freq='1H'),
    'open': np.random.rand(200) * 100,
    'high': np.random.rand(200) * 100,
    'low': np.random.rand(200) * 100,
    'close': np.random.rand(200) * 100,
    'volume': np.random.rand(200) * 1000
}
df = pd.DataFrame(data)

print("Testing AIAnaliz.hesapla_olasilik...")
try:
    result = AIAnaliz.hesapla_olasilik(df)
    print(f"Result: {result}")
    
    if "olasilik" in result:
        print("SUCCESS: AI Analysis completed without error.")
    else:
        print("FAILURE: Unexpected result format.")
except Exception as e:
    print(f"FAILURE: Exception occurred: {e}")
