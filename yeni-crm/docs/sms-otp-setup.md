# SMS OTP — NetGSM Yapılandırması

Kurye giriş ekranında telefon numarasına 6 haneli kod göndermek için NetGSM REST v2 entegrasyonu.

## Gerekli Render env değişkenleri

Render dashboard → backend servisi (`crmcatkapinda-v3-api`) → **Environment** sekmesi → şunları ekle:

| Key | Value | Açıklama |
|---|---|---|
| `SMS_PROVIDER` | `netgsm` | Sağlayıcı seçimi |
| `SMS_API_URL` | `https://api.netgsm.com.tr/sms/rest/v2/send` | NetGSM REST v2 endpoint |
| `SMS_NETGSM_USERNAME` | `<NetGSM kullanıcı adın>` | Hesap kullanıcı adı |
| `SMS_NETGSM_PASSWORD` | `<NetGSM şifren>` | Hesap şifresi |
| `SMS_SENDER` | `CATKAPINDA` | NetGSM panelinde onaylı mesaj başlığı |

> **Not:** `SMS_SENDER` değeri NetGSM panelinde önceden onaylanmış olmalı. Mevcut v2 sisteminde hangi başlık kullanılıyorsa onu yaz.

## Doğrulama

Env'ler eklendikten sonra Render servisi otomatik restart olur. Bittikten sonra:

1. `https://crmcatkapinda-v3-api.onrender.com/api/courier/login/request-otp` POST'a body:
   ```json
   {"phone": "0555..."}
   ```
2. Cevap olarak SMS düşmeli ve şu yapı dönmeli:
   ```json
   {
     "sent": true,
     "masked_phone": "0 555 *** ** 78",
     "expires_in_seconds": 300,
     "cooldown_seconds": 0
   }
   ```

## Akış (kurye gözünden)

1. `kurye.catkapinda.com` (ya da `/kurye`) açılır
2. Telefon numarası girer → "Kod Gönder"
3. SMS gelir: `Cat Kapinda CRM giris kodu: 123456 Kod 5 dakika gecerlidir.`
4. 6 haneli kodu girer → giriş yapılır

## Güvenlik

- Kod sha256 ile hash'lenip DB'ye yazılır (clear text yok)
- 5 dakika TTL
- Maks 5 yanlış deneme sonra OTP geçersiz
- 60 saniye boyunca aynı numaraya yeniden kod istenemez (rate limit)
- Personel telefon numarası `personnel.phone` ile eşleşmeli, status='Aktif' olmalı

## SMS gelmiyorsa fallback

Kurye giriş ekranında "**SMS gelmiyor mu? Personel kodu ile gir**" linki var. Bu eski yöntemi kullanır:
- Personel kodu (örn `CK-K42`)
- TC son 4 hane

İkisi de geçerli paralel akış. SMS provider'ı yapılandırılmamış olsa bile fallback çalışır, kuryeler kapanmaz.

## Maliyet

- NetGSM toplu SMS paketleri: ~10 kuruş/SMS (paket büyüklüğüne göre değişir)
- 50 kurye × ayda ~5 giriş = 250 SMS/ay → ~25 ₺/ay (yüksek tahmin)
