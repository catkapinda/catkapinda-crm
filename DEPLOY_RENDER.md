# Render Uzerinden Yayin Alma

Bu proje `Render` uzerinde calisacak sekilde hazirlandi. Onerilen yayin adresi:

- `https://crmcatkapinda.com`
- istege bagli yonlendirme: `https://www.crmcatkapinda.com`

## Neden Render?

- Ozel domain destekler.
- Ucretsiz SSL/TLS sertifikasi verir.
- Streamlit uygulamalari icin tek servisle temiz kurulum sunar.
- `render.yaml` ile tekrar kurulabilir altyapi saglar.

## Gerekli Ortam Degiskeni

Render servisinde su degiskeni tanimla:

- `DATABASE_URL`

Not:

- Uygulama bu degisken varsa PostgreSQL kullanir.
- Bu degisken yoksa yerel SQLite'a duser. Render uzerinde bu istenmez.

## Kurulum Adimlari

1. Bu projeyi GitHub reposuna yukle.
2. Render panelinde `New +` > `Web Service` sec.
3. GitHub reposunu bagla.
4. Render `render.yaml` dosyasini algilasin.
5. Servis olustuktan sonra `Environment` bolumune gidip `DATABASE_URL` degerini ekle.
6. Ilk deploy tamamlandiginda gecici `onrender.com` adresi uzerinden uygulamayi test et.

## Domain Baglama

1. Render servisinde `Settings` > `Custom Domains` bolumune gir.
2. `crmcatkapinda.com` alan adini ekle.
3. Render'in verdigi DNS kayitlarini domain saglayicina gir.
4. Istersen `www.crmcatkapinda.com` alan adini da ekleyip ana domaine yonlendir.
5. SSL sertifikasi Render tarafinda otomatik tanimlanir.

## Onerilen Canli Ayarlar

- Ana domain: `crmcatkapinda.com`
- Opsiyonel ikinci domain: `www.crmcatkapinda.com`
- Veritabani: Supabase PostgreSQL `DATABASE_URL`

## Deploy Sonrasi Kontrol Listesi

- Giris ekrani aciliyor mu?
- Personel Yonetimi aciliyor mu?
- Restoran Yonetimi aciliyor mu?
- PDF indirme calisiyor mu?
- Veriler Supabase tarafina yaziliyor mu?
- Domain `https://crmcatkapinda.com` uzerinden sorunsuz aciliyor mu?
