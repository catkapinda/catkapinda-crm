"use client";

import Link from "next/link";
import { useEffect, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "../auth/auth-provider";
import { filterSidebarItems, resolveDefaultPath, sidebarItems } from "../../lib/navigation";

export function AppShell({
  children,
  activeItem = "Genel Bakış",
}: {
  children: React.ReactNode;
  activeItem?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();

  const visibleItems = useMemo(
    () => filterSidebarItems(user?.allowed_actions ?? []),
    [user?.allowed_actions],
  );
  const canViewActiveItem = useMemo(
    () => visibleItems.some((item) => item.label === activeItem),
    [visibleItems, activeItem],
  );

  useEffect(() => {
    if (loading) {
      return;
    }
    if (!user) {
      const nextValue = pathname && pathname !== "/login" ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${nextValue}`);
      return;
    }
    if (!canViewActiveItem) {
      router.replace(resolveDefaultPath(user.allowed_actions));
    }
  }, [canViewActiveItem, loading, pathname, router, user]);

  if (loading || !user || !canViewActiveItem) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          padding: "24px",
        }}
      >
        <div
          style={{
            width: "min(420px, 100%)",
            padding: "28px",
            borderRadius: "28px",
            background: "var(--surface-strong)",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
          }}
        >
          <div
            style={{
              height: "10px",
              borderRadius: "999px",
              background: "rgba(15, 95, 215, 0.1)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: "42%",
                height: "100%",
                background: "var(--accent)",
                borderRadius: "999px",
              }}
            />
          </div>
          <h2 style={{ margin: "18px 0 10px" }}>v2 oturum hazırlanıyor</h2>
          <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
            Kimlik ve yetki bilgileri kontrol ediliyor. Bu sayfa sadece ilgili modülleri açacak.
          </p>
        </div>
      </div>
    );
  }

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
        <div style={{ marginBottom: "22px" }}>
          <div
            style={{
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
              marginTop: "8px",
              color: "var(--muted)",
              fontSize: "0.93rem",
              lineHeight: 1.6,
            }}
          >
            v2 yetkili operasyon kabuğu
          </div>
        </div>
        <nav
          style={{
            display: "grid",
            gap: "10px",
          }}
        >
          {visibleItems.map((item) => (
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

        <div
          style={{
            marginTop: "auto",
            paddingTop: "18px",
            display: "grid",
            gap: "10px",
          }}
        >
          <div
            style={{
              padding: "14px 16px",
              borderRadius: "18px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.82)",
            }}
          >
            <div style={{ fontWeight: 800 }}>{user.full_name}</div>
            <div style={{ marginTop: "4px", color: "var(--muted)", fontSize: "0.9rem" }}>
              {user.role_display}
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              void logout().then(() => router.replace("/login"));
            }}
            style={{
              padding: "12px 16px",
              borderRadius: "16px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.82)",
              color: "var(--text)",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Oturumu Kapat
          </button>
        </div>
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
