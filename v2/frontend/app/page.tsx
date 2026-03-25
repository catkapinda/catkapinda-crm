import { AppShell } from "../components/shell/app-shell";

const migrationCards = [
  {
    title: "Kimlik ve Rol Katmanı",
    body: "Telefon, e-posta ve SMS tabanlı giriş akışı backend API üstüne taşınacak.",
  },
  {
    title: "Puantaj V2",
    body: "Günlük puantaj ilk taşınacak ekran olacak; kısmi güncellemeler ve hızlı formlar burada başlayacak.",
  },
  {
    title: "Satıştan Operasyona",
    body: "Satış fırsatlarının şube açılışına dönüşmesi ayrı iş akışı olarak modelleniyor.",
  },
];

export default function HomePage() {
  return (
    <AppShell activeItem="Genel Bakış">
      <section
        style={{
          display: "grid",
          gap: "18px",
        }}
      >
        <div
          style={{
            padding: "28px",
            borderRadius: "28px",
            background: "var(--surface-strong)",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
          }}
        >
          <div
            style={{
              display: "inline-flex",
              padding: "7px 12px",
              borderRadius: "999px",
              background: "var(--accent-soft)",
              color: "var(--accent)",
              fontSize: "0.78rem",
              fontWeight: 800,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
            }}
          >
            V2 Hazırlanıyor
          </div>
          <h1
            style={{
              margin: "16px 0 10px",
              fontSize: "clamp(2rem, 4vw, 3.3rem)",
              lineHeight: 1.05,
            }}
          >
            Cat Kapinda CRM için daha hızlı ve daha kontrollü bir uygulama katmanı.
          </h1>
          <p
            style={{
              margin: 0,
              maxWidth: "70ch",
              color: "var(--muted)",
              fontSize: "1.02rem",
              lineHeight: 1.7,
            }}
          >
            Bu shell, mevcut Streamlit sistemi canlı tutarken attendance, auth, sales ve reporting
            akışlarını kademeli biçimde FastAPI ve Next.js üzerine taşımak için hazırlandı.
          </p>
        </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: "16px",
          }}
        >
          {migrationCards.map((card) => (
            <article
              key={card.title}
              style={{
                padding: "20px",
                borderRadius: "22px",
                background: "var(--surface)",
                border: "1px solid var(--line)",
                backdropFilter: "blur(8px)",
              }}
            >
              <h2
                style={{
                  margin: "0 0 10px",
                  fontSize: "1.02rem",
                }}
              >
                {card.title}
              </h2>
              <p
                style={{
                  margin: 0,
                  color: "var(--muted)",
                  lineHeight: 1.6,
                }}
              >
                {card.body}
              </p>
            </article>
          ))}
        </div>

        <a
          href="/attendance"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: "fit-content",
            padding: "14px 18px",
            borderRadius: "16px",
            background: "var(--accent)",
            color: "#fff",
            fontWeight: 800,
            letterSpacing: "0.01em",
          }}
        >
          Attendance slice ekranini ac
        </a>
      </section>
    </AppShell>
  );
}
