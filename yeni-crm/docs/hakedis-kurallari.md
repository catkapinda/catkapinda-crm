# Hakediş ve Faturalandırma Kuralları

> Bu dosya iş kurallarının kanonik kaynağıdır. Hakediş motoru (`app/services/hakedis.py`) bu kurallara göre yazılır. Değişiklik gerekirse önce burayı güncelle, sonra koda yansıt.

## 1. Anlaşma Tipleri (`restaurants.pricing_model`)

| Tip | Açıklama | Örnek Restoran |
|-----|----------|----------------|
| `hourly_only` | Sadece saat × ücret | Doğu Otomotiv (saatlik 295 ₺) |
| `hourly_plus_package` | Saatlik + paket başına prim | Quick China, SushiCo, Köroğlu Pide, Burger@, Fasuli, Dönerci Celal Usta — saat 250 ₺ + paket 25 ₺ |
| `threshold_package` | Saatlik + eşikli prim (varsayılan eşik 390 paket) | Hacıbaşar — saat 250 ₺, ≤390: 20 ₺/paket, >390: 25 ₺/paket |
| `fixed_monthly` | Aylık sabit tutar (saat/paket sayılmaz) | Sushi Inn, SC Petshop |

## 2. KDV Mantığı

- Kuryeye ödediğimiz tutar **KDV dahil** kabul edilir (kurye Çat Kapında'ya fatura keser, biz net öderiz, KDV içeride).
- Restorana **+KDV** ile fatura keseriz. KDV oranı `restaurants.vat_rate` (genellikle %20).
- Yani: `restaurants.fixed_monthly_fee` = KDV hariç tutar; restorana yansıyan = `fixed_monthly_fee × (1 + vat_rate/100)`.

## 3. Standart Kurye Hakediş Hesabı (Ana Atama)

Kuryenin ana atandığı restoranda yaptığı puantajlar için:

```
hourly_only       → worked_hours × hourly_rate
hourly_plus_package → worked_hours × hourly_rate + package_count × package_rate
threshold_package → worked_hours × hourly_rate + (
    aylık_toplam_paketleri > package_threshold
      ? aylık_toplam_paketleri × package_rate_high
      : aylık_toplam_paketleri × package_rate_low
)
fixed_monthly     → personnel.monthly_fixed_cost (ay başına sabit, kuryenin alanı)
```

**Eşikli mantık önemli:** Eşik karşılaştırması kuryenin ay boyunca o restorandaki TÜM paket toplamı ile yapılır. 390'ı geçtiyse tüm paketler yüksek tarifeye çevrilir (sadece eşiği aşan kısım değil).

## 4. Destek Vardiyası (`coverage_type = 'Destek'`)

Bir kurye, ay içinde **kendi ana restoranı dışında** başka bir restoranda da çalışmış olabilir. Bu durumda destek satırları için:

> **Destek gittiği restoranın kendi standart kurye hesabı uygulanır**, kuryenin kendi tarifesi değil.

### Eşikli restorana destek olunca

> Destek paketleri **kuryenin ana restoranındaki paket toplamına EKLENMEZ**. Eşik karşılaştırması, sadece destek günlerindeki paket toplamı ile yapılır. Kuryenin ana restoranı 380 paket atmış olsa, başka restorana destek gidip 30 paket daha attığında **tüm paketleri yüksek tarifeye çevrilmez** — çünkü "kendi bağlı olduğu restoranda 390'ı geçmesi gerekiyor."

### Aylık sabit restorana destek olunca

> Destek günü için `destek_yerin_atanmış_kuryesinin.monthly_fixed_cost ÷ 30 × destek_günü` kuryeye yansır.
> Örnek: Quick China kuryesi SC Petshop'a 1 gün destek → SC Petshop'un atanmış kuryesi Seyfullah'ın monthly_fixed_cost (73.600 ₺) ÷ 30 = **2.453,33 ₺** o gün için.

### PDF satır formatı

```
Destek vardiyası — SushiCo Beyoğlu (3 gün) — 4.500 ₺
```

## 5. Restorana Fatura Hesabı

Restorana ay sonu kesilen tutar:

```
hourly_only       → SUM(worked_hours) × hourly_rate
hourly_plus_package → SUM(worked_hours) × hourly_rate + SUM(package_count) × package_rate
threshold_package → SUM(worked_hours) × hourly_rate + (eşikli tarife)
fixed_monthly     → fixed_monthly_fee + (ekstra destek günleri için fixed_monthly_fee/30 × ekstra_gün)
```

> **Aylık sabit ekstra gün örneği:** SC Petshop kuryesi 31 gün boyunca mesai yaptıysa restorana fatura: `79.800 + 79.800/30 × 1 = 82.460 ₺` (KDV hariç). +KDV ile keserim.

## 6. Sabit Aylık Anlaşmalı Yöneticiler / Takım Şefleri

> Bazı kişiler (Restoran Takım Şefi, Kaptan, Bölge Müdürü) saat+prim bir restoranda çalışsa bile **iki ayrı sabit tutar** ile anlaşmalıdır:
> - `personnel.monthly_fixed_cost` → kuryeye ödediğimiz aylık net (örn Recep 72.050 ₺)
> - `personnel.fixed_monthly_billing` → restorana yansıyan KDV hariç sabit aylık (örn Recep için Quick China'ya 84.500 ₺ + KDV)
>
> Hakediş motoru kuralı:
> - Eğer `personnel.fixed_monthly_billing > 0` ve `working_days > 0`:
>   - **Restoran fatura formülü atlanır** (saat × tarife yapılmaz)
>   - Restorana yansıyan = `fixed_monthly_billing` (sabit)
>   - Aradaki fark kar olarak yazılır (kişi attığı paket/saatten ötürü ek kazanç sağlamaz)
> - `fixed_monthly_billing = 0` ise standart formül (saat × tarife + paket × prim)

**Recep örneği (Quick China takım şefi, Mart 2026):**
- 296 saat, 85 paket attı (standart formül 85.304 ₺ verirdi — UYGULANMAZ)
- Restorana fatura: **84.500 ₺ KDV hariç** (101.400 ₺ KDV dahil)
- Recep'e net hakediş: **72.050 ₺**
- Kar farkı: **12.450 ₺**

> **Saatlik / saat+prim restoranlarda atılan paket sabit anlaşmalı kişiye ödenen tutarı değiştirmez.** Attığı her paket bana kar yazılır.

## 7. Aylık Sabit Restoranda Ekstra Mesai Hesabı

> SC Petshop kuryesi normal 30 gün üzerinden 73.600 ₺ alıyor. Bir ay 31 gün çalışırsa (yani 1 gün ekstra mesai):
> - Kuryeye: `73.600 + 73.600/30 × 1 = 76.053 ₺`
> - Restorana: `79.800 + 79.800/30 × 1 = 82.460 ₺` (KDV hariç)

## 8. Joker (`coverage_type = 'Joker'`)

Joker = dış kurye (Çat Kapında ekibinden değil). Aylık 88.000 ₺ KDV dahil sabit tarife.
**Joker maliyeti hakediş hesabına dahil edilmez** — ayrı bir provider giderİ olarak değerlendirilir ve restorana fatura için ele alınır.

## 9. Henüz Netleşmemiş / Veri Eksiklikleri

- ⚠ **Sushi Inn**: `restaurants.fixed_monthly_fee = 79,8` virgülle girilmiş; doğrusu **79.800** olmalı. Restoran düzenleme modalından düzeltilebilir.
- ⚠ **Sushi Inn kuryeleri** (Yusuf, Hayrettin): `personnel.monthly_fixed_cost = 0`. Doğru tutarı bilmiyoruz, kullanıcıdan alınacak.
- ⚠ **Joker faturalandırması**: 88.000 ₺ KDV dahil tutarın hangi tarafa nasıl yansıdığı (restoran fatura veya operasyon gideri) netleştirilecek.
- ⚠ **`standard_daily_hours` kolonu yok**: Aylık sabit anlaşmalı restoranlarda günlük standart saat (SC Petshop & Sushi Inn için 10 saat) ayrı bir kolonda tutulmalı. Şu an hakediş motorunda `DEFAULT_FIXED_DAILY_HOURS = 10` hardcoded.

## 10. Veri Tutarlılığı Notları (ÖNEMLİ)

`daily_entries` tablosundaki bazı satırlarda **`absence_reason` ve `status` arasında tutarsızlık** var:
- `coverage_type='Destek'` + `status='Normal'` + `worked_hours=10` ise kurye **çalışmış** (örn. Erkan, Ömer, Umut SC Petshop'a destek).
- Aynı satırda `absence_reason='Diğer'` yazsa bile **bu yanıltıcı** — kurye gelmiş ve çalışmış.
- **Kural:** Hakediş motoru "çalıştı/çalışmadı" kararını **`worked_hours > 0`** üzerinden verir. `absence_reason` etiketi tek başına dikkate alınmaz.

## 11. Aylık Sabit Restoran — Ekstra Mesai Hesabı (ÖRNEKLERLE)

SC Petshop için Mart 2026 verisi:
- Seyfullah 26 gün çalışmış, **270 saat** (bir gün 20 saat = 1 gün ekstra mesai)
- `standard_daily_hours = 10`
- `expected_hours = 26 × 10 = 260`
- `extra_hours = 270 − 260 = 10`
- `extra_days = 10 / 10 = 1`
- `extra_billing = 1 × (79.800 / 30) = 2.660 ₺`
- **Seyfullah'ın restoran faturası**: 79.800 + 2.660 = **82.460 ₺ KDV hariç**
- Destek gelen 3 kişi (her biri 1 gün × 10 saat): 3 × 2.660 = **7.980 ₺ KDV hariç**
- **SC Petshop Mart 2026 toplam KDV hariç fatura**: 82.460 + 7.980 = **90.440 ₺**
- KDV %20 = 18.088 ₺ → **KDV dahil 108.528 ₺**
