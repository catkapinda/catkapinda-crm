const sidebarItems = [
  "Genel Bakış",
  "Puantaj",
  "Personel",
  "Restoranlar",
  "Satış",
  "Raporlar",
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: "280px 1fr",
      }}
    >
      <aside
        style={{
          padding: "28px 24px",
          borderRight: "1px solid rgba(193, 209, 232, 0.9)",
          background: "rgba(255, 255, 255, 0.72)",
          backdropFilter: "blur(14px)",
        }}
      >
        <div
          style={{
            marginBottom: "22px",
            color: "#17345D",
            fontWeight: 900,
            fontSize: "1.45rem",
            letterSpacing: "-0.03em",
          }}
        >
          Cat Kapinda CRM
        </div>
        <div
          style={{
            marginBottom: "20px",
            color: "var(--muted)",
            fontSize: "0.93rem",
            lineHeight: 1.6,
          }}
        >
          Fast, role-aware operations shell for the v2 migration track.
        </div>
        <nav
          style={{
            display: "grid",
            gap: "10px",
          }}
        >
          {sidebarItems.map((item, index) => (
            <div
              key={item}
              style={{
                padding: "14px 16px",
                borderRadius: "18px",
                border: "1px solid var(--line)",
                background: index === 1 ? "var(--accent-soft)" : "rgba(255, 255, 255, 0.82)",
                color: index === 1 ? "var(--accent)" : "var(--text)",
                fontWeight: 700,
              }}
            >
              {item}
            </div>
          ))}
        </nav>
      </aside>
      <main
        style={{
          padding: "28px",
        }}
      >
        {children}
      </main>
    </div>
  );
}
