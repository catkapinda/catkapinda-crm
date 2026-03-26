import Link from "next/link";

const sidebarItems = [
  { label: "Genel Bakış", href: "/" },
  { label: "Puantaj", href: "/attendance" },
  { label: "Personel", href: "/personnel" },
  { label: "Restoranlar", href: "#" },
  { label: "Satış", href: "#" },
  { label: "Raporlar", href: "#" },
];

export function AppShell({
  children,
  activeItem = "Genel Bakış",
}: {
  children: React.ReactNode;
  activeItem?: string;
}) {
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
          {sidebarItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              style={{
                padding: "14px 16px",
                borderRadius: "18px",
                border: "1px solid var(--line)",
                background: item.label === activeItem ? "var(--accent-soft)" : "rgba(255, 255, 255, 0.82)",
                color: item.label === activeItem ? "var(--accent)" : "var(--text)",
                fontWeight: 700,
              }}
            >
              {item.label}
            </Link>
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
