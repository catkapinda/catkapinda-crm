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

> Bazı kişiler (Restoran Takım Şefi, Kaptan vb.) saat+prim bir restoranda çalışsa bile **aylık sabit** anlaşma ile çalışır. Bu durumda:
> - `personnel.monthly_fixed_cost > 0` ise → o tutar kuryenin aylık net hakedişidir, formül uygulanmaz
> - O kişinin attığı paket / saat **bana kar olarak yansır** (restoran üzerinden saat+prim baz hesabı yapılıp fatura kesilir, kişi sabit alır, fark kar)

**Recep örneği:**
- Quick China takım şefi
- Restorana fatura: 84.500 ₺ + KDV (101.400 ₺ KDV dahil)
- Recep'e net hakediş: 72.050 ₺ aylık sabit
- Aradaki 12.450 ₺ kar (paket atışından bağımsız)

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
