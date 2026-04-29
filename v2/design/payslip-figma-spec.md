# Kurye Hakediş Belgesi

Bu belge, mevcut PDF tasarımını daha premium, daha kurumsal ve daha fintech-grade bir çizgiye taşımak için Figma-first referansıdır.

## Tasarım Niyeti

- Dashboard gibi değil, finansal statement gibi hissettirmeli.
- Kullanıcı 3 saniyede şu akışı anlamalı:
  - Brüt ne kadar?
  - Ne kadar kesinti var?
  - Eline net ne geçiyor?
- Güven hissi vermeli.
- Fazla kart, fazla border ve gereksiz açıklama metinlerinden kaçınmalı.

## Frame

- Canvas: `A4 Portrait`
- Ölçü: `794 x 1123 px`
- Safe content width: `698 px`
- Outer margin:
  - top `56`
  - right `48`
  - bottom `48`
  - left `48`
- Spacing grid: `8 px`
- Ana section gap: `24 px`
- İç blok gap: `16 px`

## Renk Sistemi

- Page background: `#F6F8FB`
- Paper/card background: `#FFFFFF`
- Primary text: `#0F172A`
- Secondary text: `#667085`
- Hairline border: `#E7ECF3`
- Divider: `#EEF2F7`
- Brand blue: `#1D4ED8`
- Net green: `#16A34A`
- Deduction red: `#DC2626`
- Soft green fill: `#ECFDF3`
- Soft red fill: `#FEF2F2`
- Soft neutral fill: `#F8FAFC`

## Tipografi

- Title:
  - `26 px`
  - `Semibold`
  - line-height `1.05`
  - color `#0F172A`
- Section title:
  - `13 px`
  - `Semibold`
  - tracking `0`
  - color `#0F172A`
- Meta label:
  - `11 px`
  - `Medium`
  - color `#667085`
- Body:
  - `13 px`
  - `Regular`
  - color `#344054`
- Large value:
  - `18 px`
  - `Semibold`
  - color `#0F172A`
- Hero net value:
  - `24 px`
  - `Bold`
  - color `#16A34A`
- Financial flow values:
  - gross `18 px / 700`
  - deductions `18 px / 700 / red`
  - net `22 px / 800 / green`

## Yüzey Dili

- Radius:
  - outer cards `16 px`
  - small chips `999 px`
- Shadow:
  - `0 10px 30px rgba(15, 23, 42, 0.05)`
- Border:
  - sadece ince, açık gri
  - heavy stroke yok
- Büyük bloklarda dolu renk yerine hafif tint kullanılmalı

## Yerleşim

### 1. Header

- Tek white card
- Yükseklik yaklaşık `116 px`
- Sol:
  - logo `88 x 88`
  - logo tam görünür, crop yok
  - wordmark görünmüyorsa logonun altına küçük brand label eklenmez
- Orta:
  - `Kurye Hakediş Belgesi`
  - alt satır:
    - `Mart 2026`
    - dot separator
    - `Oluşturma: 29.04.2026`
- Sağ:
  - ayrı renkli büyük kutu yok
  - boş alan bırakılmalı
  - header nefes almalı

### 2. Financial Flow

- Ayrı tek white card
- Ortalanmış horizontal flow
- Yapı:
  - label row:
    - `Brüt Kazanç`
    - `Toplam Kesinti`
    - `Net Ödeme`
  - value row:
    - `72.440,00 ₺`
    - `–`
    - `13.000,00 ₺`
    - `=`
    - `59.440,00 ₺`
- Operators:
  - minus ve equal işaretleri aynı baseline'da
  - muted neutral
- Alt satırda küçük secondary line:
  - `Fatura Matrahı ... • KDV ... • Tevkifat ...`
  - finansal ama bağırmayan bir bilgi satırı

### 3. Content Grid

- 2 kolon
- Sol kolon genişlik: `%58`
- Sağ kolon genişlik: `%42`
- Gap: `24 px`

#### Sol kart: Personel + Çalışma Özeti

- Üstte sadece isim:
  - `Murat Tırın`
  - tek satır
- Altında 3 kolon meta:
  - `Kod`
  - `Rol`
  - `Durum`
- Sonra ince divider
- Divider altı 3 kolon çalışma:
  - `Saat`
  - `Paket`
  - `Şube`
- Çalışma değerleri güçlü ama aşırı büyük değil

#### Sağ kart: Çalışılan Restoranlar

- Başlık:
  - `Çalışılan Restoranlar`
- Sağ üstte küçük chip:
  - `1 şube`
- Alt kısa açıklama:
  - secondary color
- Restoran adı:
  - güçlü text
  - 1 veya 2 satır içinde kontrollü

### 4. Deductions Table

- Geniş white card
- Üst satır:
  - sol: `Kesinti Kalemleri`
  - sağ: `Toplam Kesinti 13.000,00 ₺`
- Başlık ile toplam aynı hizaya oturmalı
- Toplam kesinti sağda küçük tinted red badge veya sade red text line olabilir
- Tablo:
  - columns:
    - `Kalem`
    - `Tutar`
  - tutar kolonu right aligned
  - row separators very light
  - zebra yok
  - sadece negatifler kırmızı

## Bileşen Listesi

- `HeaderCard`
- `FinancialFlowCard`
- `PersonSummaryCard`
- `RestaurantCard`
- `DeductionTable`
- `MetaItem`
- `MetricValue`
- `PillBadge`

## Figma Auto Layout

- Tüm ana kartlarda auto-layout dikey
- Padding:
  - cards `24`
  - compact cards `20`
- Gap:
  - section içi `16`
  - micro gap `8`
- Tablo:
  - başlık row auto-layout horizontal
  - body row min height `40`

## Kaçınılacaklar

- Header içinde büyük renkli KPI kutusu
- Gereksiz ikinci kez `Net Ödeme` vurgusu
- Kalın border
- Dashboard hissi veren 4-5 farklı renkli kutu
- Çok büyük logo veya crop’lu logo
- Alt alta yığılan çok açıklama
- Kırılan isimler
- Üst üste binen finansal değerler

## PDF'e Taşıma Notları

- Logo beyaz zeminde kullanılmalı
- Metin wrap kuralları:
  - kişi adı kırılmamalı
  - finansal değerler tek satır kalmalı
  - restoran adı kontrollü 2 satıra kadar inebilir
- Tüm para değerleri:
  - `70.730,00 ₺`
- Tablo ve flow alanı için fixed coordinate yerine measured layout kullanılmalı

## Son Hedef Cümlesi

Bu belge, bir CRM export'u gibi değil; Stripe fatura özeti ile modern maaş pusulası arasında duran, sade, güven veren, premium bir finans belgesi gibi görünmeli.
