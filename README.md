# AliBaba IPTV Grup Editör

## Özellikler
- Manuel mod: Tek IPTV (M3U Plus) linkini analiz eder, grupları listeler, seçilen gruplarla yeni playlist oluşturur.
- Otomatik mod: Metin içinden IPTV linklerini bulur, çalışan linkleri test eder, grup başındaki ülke koduna (TR/DE/RO vb.) göre filtreleyip çıktı üretir.
- Çıktı: `m3u` / `m3u8` seçimi, otomatik adlandırma ve sürümleme (`v1, v2, ...`).

## Yerelde Çalıştırma

```bash
pip install -r requirements.txt
python main.py
```

## APK Alma (Yerel)
Buildozer Linux ortamı gerektirir (Windows’ta genelde WSL/VM ile kullanılır).

```bash
pip install buildozer
buildozer -v android debug
```
APK dosyası `bin/` klasörüne gelir.

## GitHub Actions ile APK
- Repo’yu GitHub’a yükle.
- `main` branch’ine push yap.
- GitHub -> Actions -> `Android APK (Buildozer)` workflow çalışır.
- Build bitince `Artifacts` bölümünden APK indir.
