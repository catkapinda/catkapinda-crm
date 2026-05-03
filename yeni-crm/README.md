# Çat Kapında CRM v3

Sıfırdan inşa edilmiş, temiz mimarili kurye yönetim sistemi.

## Yapı

```
yeni-crm/
├── frontend/         # Next.js 15 + TypeScript + Tailwind
│   ├── src/
│   │   ├── app/      # Next App Router sayfaları
│   │   ├── components/
│   │   └── lib/
│   └── package.json
├── backend/          # FastAPI + psycopg + Pydantic
│   ├── app/
│   │   ├── api/routes/
│   │   ├── core/     # config, database
│   │   ├── services/ # iş mantığı
│   │   └── main.py
│   └── pyproject.toml
├── design/           # HTML mock-up'lar (referans)
└── docs/
```

## Teknoloji Yığını

**Frontend**
- Next.js 15 (App Router, RSC)
- TypeScript
- Tailwind CSS (Çat Kapında saks mavisi tema)
- TanStack Query (data fetching)
- Recharts (grafikler)
- Inter Tight + Bricolage Grotesque + JetBrains Mono fontları

**Backend**
- FastAPI 0.115+
- Python 3.12+
- psycopg 3 (Postgres bağlantısı)
- Pydantic v2 (validation)
- Pydantic Settings (config)

**Veritabanı**
- Supabase Postgres (existing — Mart 2026 verisi yedekli)

## Kurulum

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # macOS/Linux
# veya: .venv\Scripts\activate    # Windows
pip install -e ".[dev]"

cp .env.example .env
# .env'yi düzenle — DATABASE_URL'i gir

uvicorn app.main:app --reload --port 8000
# http://localhost:8000/docs → API dokümanı
```

### 2. Frontend

```bash
cd frontend
npm install

cp .env.example .env.local

npm run dev
# http://localhost:3000 → Genel Bakış
```

## Geliştirme Akışı

1. **Tasarım onayı:** `/design/*.html` referansa bakılır
2. **Backend endpoint'i:** `app/api/routes/` altına eklenir, servis `app/services/` altında
3. **Frontend sayfası:** `src/app/` altında oluşturulur, component'lar `src/components/`
4. **Veri çekme:** TanStack Query + fetch wrapper'ı `lib/api.ts`'de

## Render Deploy

- **Backend:** `crmcatkapinda-v3-api` (Python service)
- **Frontend:** `crmcatkapinda-v3` (Node service)

`render.yaml` dosyaları sonra eklenecek.

## Mevcut Yedek

`/data-backup-20260503/` klasöründe Supabase'in tam yedeği:
- 19 tablo
- 6,698 kayıt
- 92 aktif personel
- Mart 2026 verileri

## Sıradaki Adımlar

- [ ] Restoran sayfası
- [ ] Restoran ekleme formu (4 anlaşma tipi)
- [ ] Hakediş Onayları sayfası
- [ ] Restoran/Kurye onay sayfaları (link tıklayınca)
- [ ] Avans Talepleri
- [ ] PDF hakediş üretimi (reportlab)
- [ ] SMS gönderim entegrasyonu (NETGSM)
- [ ] crmcatkapinda.com → v3 cutover
