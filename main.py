import time
from data_loader import fetch_binance_ohlcv
from analyzers import TeknikAnaliz, OnChainAnaliz, TemelAnaliz, SosyalAnaliz

def main():
    """
    Ana çalışma döngüsü. Veri çeker ve analiz modüllerini çalıştırır.
    """
    symbol = 'BTC/USDT'
    print(f"{symbol} için takip ve analiz sistemi başlatılıyor... (Çıkış için CTRL+C)")

    # Analiz sınıflarını başlat (statik metodlar kullanıldığı için aslında gerek yok ama yapı olarak dursun)
    teknik = TeknikAnaliz()
    onchain = OnChainAnaliz()
    temel = TemelAnaliz()
    sosyal = SosyalAnaliz()

    try:
        while True:
            print("-" * 50)
            # Veriyi çek (Teknik analiz için en az 20-50 mum gerekli, 100 çekiyoruz)
            df = fetch_binance_ohlcv(symbol, timeframe='1m', limit=100)

            if df is not None and not df.empty:
                # --- VERİ ÖZETİ ---
                last_price = df['close'].iloc[-1]
                timestamp = df['timestamp'].iloc[-1]
                print(f"[{timestamp}] Fiyat: {last_price} USDT")

                # --- TEKNİK ANALİZ ---
                # RSI Hesapla
                df['RSI'] = teknik.hesapla_rsi(df)
                son_rsi = df['RSI'].iloc[-1]
                
                # Bollinger Bantları
                bbands = teknik.hesapla_bollinger(df)
                # Sadece son değerleri alalım (Sütun isimleri genelde BBL, BBM, BBU şeklindedir)
                # pandas_ta sütun isimlendirmesi dinamik olabilir, son sütunları kontrol ediyoruz.
                if bbands is not None:
                     # Genellikle columns: [LOW, MID, UP, BANDWIDTH, PERCENT]
                     # Basitçe son satırı yazdıralım
                     son_bb = bbands.iloc[-1]
                
                print(f"\n📊 TEKNİK ANALİZ:")
                print(f"   ► RSI (14): {son_rsi:.2f}")
                # Bollinger detayını gerekirse ekleyebiliriz, şimdilik basit tutalım

                # --- ON-CHAIN (Simülasyon) ---
                onchain_sinyal = onchain.kontrol_et_hacim_anormalligi(df)
                print(f"\n🔗 ON-CHAIN ANALİZ:")
                print(f"   ► Durum: {onchain_sinyal}")

                # --- SOSYAL ANALİZ (Simülasyon) ---
                sentiment = sosyal.get_sentiment_score()
                print(f"\n🐦 SOSYAL ANALİZ:")
                print(f"   ► Skor: {sentiment['skor']} - {sentiment['durum']}")

                # --- TEMEL ANALİZ (Simülasyon) ---
                # Şimdilik sabit bir olay gönderiyoruz, ileride kullanıcıdan veya takvimden alınabilir.
                temel_yorum = temel.ekonomik_etki_hesapla("faiz kararı")
                print(f"\n🌍 TEMEL ANALİZ (Simülasyon - Örnek Olay: Faiz Kararı):")
                print(f"   ► Etki: {temel_yorum}")

            else:
                print("Veri alınamadı, bekleniyor...")

            # 30 saniye bekle
            time.sleep(30)

    except KeyboardInterrupt:
        print("\nProgram kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\nAna döngüde hata oluştu: {e}")

if __name__ == "__main__":
    main()
