import pandas as pd
import pandas_ta as ta
import numpy as np
import ccxt
from sklearn.ensemble import RandomForestClassifier

DEFAULT_AI_RESULT = {
    "AI_Skor": 50.0, 
    "Tahmin": "Yatay",
    "Setup": {"Giriş": 0, "Hedef": 0, "Stop": 0, "Potansiyel": 0},
    "Trend_1D": "-",
    "Likidite": "✅",
    "Hacim_Onay": False,
    "MACD": "-",
    "Ichimoku": "-",
    "Funding": "-",
    "Win_Rate": 0,
    "Trade_Count": 0,
    "Profit_Factor": 0,
    "MTF_Uyum": False,
    "MTF_Detay": "-",
    "Not": "-"
}

def get_trend(df) -> str:
    """Basit trend belirleme: Son 5 mum ortalaması vs son fiyat"""
    if df is None or len(df) < 5: return "?"
    close = df['close'].iloc[-1]
    avg = df['close'].iloc[-5:].mean()
    return "↑" if close > avg else "↓"

class BacktestEngine:
    @staticmethod
    def hesapla(df, atr_mult_sl=1.5, atr_mult_tp=2.5):
        try:
            if df is None or len(df) < 100:
                return {"win_rate": 0, "trade_count": 0, "profit_factor": 0}
            
            df = df.copy()
            df['RSI'] = df.ta.rsi(length=14)
            df['ATR'] = df.ta.atr(length=14)
            df.dropna(inplace=True)
            
            wins, losses, total_profit, total_loss = 0, 0, 0, 0
            test_data = df.tail(80)
            
            for i in range(20, len(test_data) - 5):
                row = test_data.iloc[i]
                rsi, atr, entry = row['RSI'], row['ATR'], row['close']
                
                if rsi < 35:
                    direction, tp, sl = "LONG", entry + (atr_mult_tp * atr), entry - (atr_mult_sl * atr)
                elif rsi > 65:
                    direction, tp, sl = "SHORT", entry - (atr_mult_tp * atr), entry + (atr_mult_sl * atr)
                else:
                    continue
                
                future = test_data.iloc[i+1:i+6]
                hit_tp, hit_sl = False, False
                
                for _, f_row in future.iterrows():
                    if direction == "LONG":
                        if f_row['high'] >= tp: hit_tp = True; break
                        if f_row['low'] <= sl: hit_sl = True; break
                    else:
                        if f_row['low'] <= tp: hit_tp = True; break
                        if f_row['high'] >= sl: hit_sl = True; break
                
                if hit_tp:
                    wins += 1
                    total_profit += abs(tp - entry)
                elif hit_sl:
                    losses += 1
                    total_loss += abs(sl - entry)
            
            total = wins + losses
            win_rate = (wins / total * 100) if total > 0 else 0
            profit_factor = (total_profit / total_loss) if total_loss > 0 else 0
            
            return {"win_rate": round(win_rate, 1), "trade_count": total, "profit_factor": round(profit_factor, 2)}
        except:
            return {"win_rate": 0, "trade_count": 0, "profit_factor": 0}

class AIAnaliz:
    @staticmethod
    def hesapla_olasilik(df_1h, df_daily=None, symbol=None, df_4h=None, df_15m=None):
        try:
            if df_1h is None or len(df_1h) < 50:
                return DEFAULT_AI_RESULT
                
            df = df_1h.copy()
            
            # Göstergeler
            df['RSI'] = df.ta.rsi(length=14)
            df['ATR'] = df.ta.atr(length=14)
            
            try:
                bb = df.ta.bbands(length=20)
                df['BBW'] = (bb.iloc[:, 2] - bb.iloc[:, 0]) / bb.iloc[:, 1] if bb is not None else 0
            except:
                df['BBW'] = 0
            
            # MACD
            macd_signal = "-"
            try:
                macd = df.ta.macd()
                if macd is not None:
                    macd_signal = "🟢" if macd.iloc[-1, 0] > macd.iloc[-1, 2] else "🔴"
            except:
                pass
            
            # Ichimoku
            ichimoku_signal = "-"
            try:
                ichi = df.ta.ichimoku()
                if ichi and len(ichi) > 0:
                    current = df['close'].iloc[-1]
                    span_a = ichi[0].iloc[-1, 2] if len(ichi[0].columns) > 2 else current
                    ichimoku_signal = "☁️↑" if current > span_a else "☁️↓"
            except:
                pass
            
            # Funding
            funding_signal = "-"
            try:
                if symbol:
                    exchange = ccxt.binance({'options': {'defaultType': 'future'}})
                    funding = exchange.fetch_funding_rate(symbol)
                    rate = float(funding.get('fundingRate', 0)) * 100
                    funding_signal = f"🔴{rate:.2f}%" if rate > 0.03 else (f"🟢{rate:.2f}%" if rate < -0.03 else f"⚪{rate:.2f}%")
            except:
                pass
            
            df['PCT_CHANGE'] = df['close'].pct_change()
            df['VOL_CHANGE'] = df['volume'].pct_change()
            df.dropna(inplace=True)
            
            if len(df) < 50:
                return DEFAULT_AI_RESULT

            # Backtest
            backtest = BacktestEngine.hesapla(df)
            
            # ML Model
            df['TARGET'] = (df['close'].shift(-1) > df['close']).astype(int)
            features = ['RSI', 'BBW', 'PCT_CHANGE', 'VOL_CHANGE']
            X = df[features]
            y = df['TARGET']
            
            clf = RandomForestClassifier(n_estimators=30, random_state=42, max_depth=4)
            clf.fit(X.iloc[:-1], y.iloc[:-1])
            prob = clf.predict_proba(X.iloc[[-1]])[0][1] * 100
            
            # === MULTI-TIMEFRAME CONFLUENCE ===
            trend_1h = get_trend(df)
            trend_4h = get_trend(df_4h) if df_4h is not None else "?"
            trend_15m = get_trend(df_15m) if df_15m is not None else "?"
            trend_1d = get_trend(df_daily) if df_daily is not None else "?"
            
            mtf_uyum = False
            mtf_detay = f"15m:{trend_15m} 1H:{trend_1h} 4H:{trend_4h}"
            
            # Üç timeframe da aynı yöndeyse = GÜÇLÜ SİNYAL
            if trend_15m == trend_1h == trend_4h:
                mtf_uyum = True
                prob = min(95, prob + 15) if trend_1h == "↑" else max(5, prob - 15)
            
            # MACD/Ichimoku boost
            if "🟢" in macd_signal and "↑" in ichimoku_signal:
                prob = min(95, prob + 5)
            elif "🔴" in macd_signal and "↓" in ichimoku_signal:
                prob = max(5, prob - 5)
            
            # Hacim
            last_vol = df['volume'].iloc[-1]
            avg_vol = df['volume'].iloc[-11:-1].mean()
            hacim_onay = last_vol / avg_vol >= 1.5 if avg_vol > 0 else False
            
            # Karar
            if prob > 51: 
                tahmin = "LONG 🚀"
            elif prob < 49: 
                tahmin = "SHORT 📉"
            else:
                tahmin = "LONG" if df['RSI'].iloc[-1] > 50 else "SHORT"
                prob = 52 if "LONG" in tahmin else 48
            
            # Likidite
            subset = df.tail(50)
            current = df['close'].iloc[-1]
            likidite = "✅"
            if abs(current - subset['high'].max()) / subset['high'].max() < 0.005:
                likidite = "⚠️"
            elif abs(current - subset['low'].min()) / subset['low'].min() < 0.005:
                likidite = "⚠️"
            
            # Setup
            atr_val = df['ATR'].iloc[-1]
            if "LONG" in tahmin:
                sl = current - (1.5 * atr_val)
                tp = current + (2.5 * atr_val)
            else:
                sl = current + (1.5 * atr_val)
                tp = current - (2.5 * atr_val)
            potansiyel = abs((tp - current) / current) * 100
            
            return {
                "AI_Skor": round(prob, 2),
                "Tahmin": tahmin,
                "Setup": {"Giriş": current, "Stop": sl, "Hedef": tp, "Potansiyel": potansiyel},
                "Trend_1D": trend_1d,
                "Likidite": likidite,
                "Hacim_Onay": hacim_onay,
                "MACD": macd_signal,
                "Ichimoku": ichimoku_signal,
                "Funding": funding_signal,
                "Win_Rate": backtest['win_rate'],
                "Trade_Count": backtest['trade_count'],
                "Profit_Factor": backtest['profit_factor'],
                "MTF_Uyum": mtf_uyum,
                "MTF_Detay": mtf_detay,
                "Not": "🎯 GÜÇLÜ" if mtf_uyum else mtf_detay
            }
        except:
            return DEFAULT_AI_RESULT

class LiquidityAnaliz:
    @staticmethod
    def kontrol_et(df):
        return "✅"

class HaberAnaliz:
    @staticmethod
    def risk_kontrol(coin_base):
        return {"risk": False, "baslik": ""}
