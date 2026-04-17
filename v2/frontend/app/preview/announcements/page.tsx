import Link from "next/link";

import { AppShell } from "../../../components/shell/app-shell";

const serifTitleStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

const paperCardStyle = {
  borderRadius: "28px",
  border: "1px solid var(--line)",
  background: "var(--surface-raised)",
  boxShadow: "var(--shadow-soft)",
} as const;

const metrics = [
  ["Giriş Deneyimi", "Yenilendi"],
  ["Personel Formları", "Güncellendi"],
  ["Restoran Fiyatlama", "Dinamik"],
  ["Motor Kira Hesabı", "Gün Bazlı"],
] as const;

const snapshots = [
  {
    title: "Operasyon ve Form Akışları",
    items: [
      ["Personel Yönetimi", "Ekleme sonrası görünür başarı mesajı ve son eklenen kartı"],
      ["Zorunlu Alanlar", "Kırmızı yıldız ile işaretlenir ve boş geçilemez"],
      ["Rol / Maliyet Modeli", "Personel formunda otomatik eşlenir"],
      ["Restoran Fiyat Modelleri", "Seçime göre sadece ilgili alanlar görünür"],
    ],
  },
  {
    title: "Finans ve Hesaplama",
    items: [
      ["Motor Kira", "13.000 / 30 x çalışılan gün formülüyle hesaplanır"],
      ["Kesinti Senkronu", "Puantaj ekleme, güncelleme ve silmede otomatik yenilenir"],
      ["Hakediş / Raporlar", "Açılırken sistem kesintileri yeniden senkronlanır"],
      ["Şifre Sıfırlama", "E-posta ve SMS ile kurtarma akışı desteklenir"],
    ],
  },
] as const;

const checklistItems = [
  [
    "1. Giriş ve durum ekranını aç",
    "Yayın sonrası önce giriş ekranını ve durum sayfasını aç. Temel omurganın ayakta olduğunu buradan hızlı görürsün.",
  ],
  [
    "2. Sert yenile ve görünür metni doğrula",
    "Eski ön bellekten kaçınmak için sayfayı sert yenile. Görsel ya da metin farkı bekleniyorsa ilk kontrolü burada yap.",
  ],
  [
    "3. Gerekirse yayını elle yeniden başlat",
    "Canlı ortamda değişiklik görünmüyorsa yayın tarafında bazen elle yeniden dağıtım gerekir. Yeniden dağıtımdan sonra tekrar sert yenilemek en güvenli kontroldür.",
  ],
] as const;

export default function PreviewAnnouncementsPage() {
  return (
    <AppShell activeItem="Duyurular">
      <div
        style={{
          display: "grid",
          gap: "22px",
        }}
      >
        <section
          style={{
            ...paperCardStyle,
            padding: "28px",
            background:
              "linear-gradient(135deg, rgba(22,39,63,0.96), rgba(38,58,86,0.95) 62%, rgba(171,114,47,0.18))",
            color: "#fff7ea",
          }}
        >
          <div
            style={{
              maxWidth: "920px",
              display: "grid",
              gap: "12px",
            }}
          >
            <div
              style={{
                fontSize: "0.76rem",
                fontWeight: 800,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "rgba(255,247,234,0.72)",
              }}
            >
              Güncellemeler ve Duyurular
            </div>
            <h1
              style={{
                ...serifTitleStyle,
                margin: 0,
                fontSize: "clamp(2.8rem, 6vw, 5.3rem)",
                lineHeight: 0.94,
                fontWeight: 700,
              }}
            >
              Sistemdeki son iyileştirmeler ve takip notları
            </h1>
            <p
              style={{
                margin: 0,
                maxWidth: "760px",
                lineHeight: 1.8,
                color: "rgba(255,247,234,0.82)",
                fontSize: "1rem",
              }}
            >
              Operasyon ekibinin son yayınlanan geliştirmeleri tek ekranda görmesi için hazırlanan
              hızlı özet alanı.
            </p>
          </div>
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "14px",
          }}
        >
          {metrics.map(([label, value]) => (
            <article
              key={label}
              style={{
                ...paperCardStyle,
                padding: "18px 18px 16px",
                background:
                  "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(246,239,228,0.96))",
              }}
            >
              <div
                style={{
                  color: "var(--muted)",
                  fontSize: "0.74rem",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  fontWeight: 800,
                }}
              >
                {label}
              </div>
              <div
                style={{
                  ...serifTitleStyle,
                  marginTop: "10px",
                  fontSize: "1.8rem",
                  lineHeight: 0.95,
                  fontWeight: 700,
                }}
              >
                {value}
              </div>
            </article>
          ))}
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "18px",
          }}
        >
          {snapshots.map((snapshot) => (
            <article
              key={snapshot.title}
              style={{
                ...paperCardStyle,
                padding: "22px",
                display: "grid",
                gap: "16px",
                background:
                  "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(249,244,235,0.95))",
              }}
            >
              <div
                style={{
                  ...serifTitleStyle,
                  fontSize: "2rem",
                  lineHeight: 0.98,
                  fontWeight: 700,
                }}
              >
                {snapshot.title}
              </div>
              <div
                style={{
                  display: "grid",
                  gap: "12px",
                }}
              >
                {snapshot.items.map(([label, value]) => (
                  <div
                    key={`${snapshot.title}-${label}`}
                    style={{
                      display: "grid",
                      gap: "6px",
                      paddingBottom: "12px",
                      borderBottom: "1px solid rgba(24,40,59,0.08)",
                    }}
                  >
                    <div
                      style={{
                        fontWeight: 800,
                        color: "var(--text)",
                      }}
                    >
                      {label}
                    </div>
                    <div
                      style={{
                        color: "var(--muted)",
                        lineHeight: 1.65,
                      }}
                    >
                      {value}
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </section>

        <section
          style={{
            ...paperCardStyle,
            padding: "22px",
            display: "grid",
            gap: "16px",
            background:
              "linear-gradient(180deg, rgba(246,249,255,0.98), rgba(238,244,255,0.95))",
          }}
        >
          <div
            style={{
              color: "#0f5fd7",
              fontWeight: 800,
              fontSize: "0.74rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            İlk Kontrol Sırası
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: "14px",
            }}
          >
            {checklistItems.map(([title, detail]) => (
              <article
                key={title}
                style={{
                  padding: "16px",
                  borderRadius: "18px",
                  border: "1px solid rgba(15,95,215,0.12)",
                  background: "rgba(255,255,255,0.78)",
                  display: "grid",
                  gap: "8px",
                }}
              >
                <div style={{ fontWeight: 800, color: "var(--text)" }}>{title}</div>
                <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>{detail}</div>
              </article>
            ))}
          </div>
        </section>

        <section
          style={{
            ...paperCardStyle,
            padding: "22px",
            display: "grid",
            gap: "10px",
            background:
              "linear-gradient(180deg, rgba(185,116,41,0.12), rgba(255,248,236,0.98))",
            border: "1px solid rgba(185,116,41,0.18)",
          }}
        >
          <div
            style={{
              color: "var(--accent-strong)",
              fontWeight: 800,
              fontSize: "0.74rem",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            Notlar
          </div>
          <div
            style={{
              color: "var(--text)",
              lineHeight: 1.75,
            }}
          >
            Canlı ortamda bir değişiklik görünmüyorsa yayın tarafında bazen elle yeniden dağıtım
            çalıştırmak gerekebilir. Yayın tamamlandıktan sonra sayfayı sert yenilemek en güvenli
            kontroldür.
          </div>
          <div
            style={{
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Bu alan sabit duyuru panosu gibi çalışır; yeni operasyon notları gerektiğinde kolayca
            genişletilebilir.
          </div>
        </section>

        <div
          style={{
            color: "var(--muted)",
          }}
        >
          Gerçek giriş yüzeyine dönmek istersen <Link href="/login">giriş ekranını aç</Link>.
        </div>
      </div>
    </AppShell>
  );
}
