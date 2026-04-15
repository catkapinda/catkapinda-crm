"use client";

import Link from "next/link";
import { useEffect, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "../auth/auth-provider";
import type { SidebarItem } from "../../lib/navigation";
import { filterSidebarItems, resolveDefaultPath, sidebarItems } from "../../lib/navigation";
import { isPreviewPathname } from "../../lib/preview";

type PreviewMeta = {
  kicker: string;
  title: string;
  description: string;
  relatedLabels: string[];
};

const previewMetaByLabel: Record<string, PreviewMeta> = {
  "Genel Bakış": {
    kicker: "Preview Hub",
    title: "Tum v2 deneyimini tek merkezden oku",
    description:
      "Preview hattinin omurgasi burada. Modulleri akisa gore ayiriyor, son sinyalleri topluyor ve nereden baslanacagini netlestiriyor.",
    relatedLabels: ["Puantaj", "Satış", "Ekipman"],
  },
  "Puantaj": {
    kicker: "Saha Omurgasi",
    title: "Gunluk puantaj akisi yeni katta",
    description:
      "Vardiya, destek gecisi ve aylik kayit temizligi gibi operasyonun en sik dokunulan islerini hizli gozlemlemek icin hazir.",
    relatedLabels: ["Personel", "Kesintiler", "Restoranlar"],
  },
  Personel: {
    kicker: "Kadro Yonetimi",
    title: "Kadro kartlari ve saha dagilimi burada toparlaniyor",
    description:
      "Kart acma, durum degistirme ve restoran dagilimi yeni dilde daha okunur bir yuzeye donusuyor.",
    relatedLabels: ["Puantaj", "Kesintiler", "Ekipman"],
  },
  Kesintiler: {
    kicker: "Bordro On Hatti",
    title: "Kesinti akisi artik daha kontrollu",
    description:
      "Manuel ve otomatik kesintileri ayni panelde gormek, duzenlemek ve payroll etkisini hissetmek icin acik.",
    relatedLabels: ["Aylık Hakediş", "Personel", "Puantaj"],
  },
  Ekipman: {
    kicker: "Filo ve Zimmet",
    title: "Zimmet, satis ve box geri alim ayni hatta",
    description:
      "Ekipman kayitlarini backoffice diliyle izlemek, duzenlemek ve box iadelerini birlikte gormek icin tasarlandi.",
    relatedLabels: ["Satın Alma", "Kesintiler", "Sistem Kayıtları"],
  },
  "Aylık Hakediş": {
    kicker: "Finans Cekirdegi",
    title: "Net odeme ve kesinti resmi buradan okunuyor",
    description:
      "Saat, paket, kesinti ve net odeme dagilimini tek panelde daha karli ve daha hizli analiz etmek icin kuruldu.",
    relatedLabels: ["Kesintiler", "Raporlar", "Satın Alma"],
  },
  "Satın Alma": {
    kicker: "Backoffice Maliyet",
    title: "Fatura ve tedarik hareketi sade ama guclu bir hatta",
    description:
      "Tedarikciler, kalem bazli alimlar ve birim maliyet resmi artik daha derli toplu bir satin alma panelinde.",
    relatedLabels: ["Ekipman", "Aylık Hakediş", "Raporlar"],
  },
  "Satış": {
    kicker: "Ticari Akis",
    title: "Pipeline ve teklif hikayesi daha ikna edici bir yuzeyde",
    description:
      "Firsat havuzu, teklif modeli ve takip aksiyonlari daha editoryal bir satista bulusuyor.",
    relatedLabels: ["Raporlar", "Restoranlar", "Satın Alma"],
  },
  Restoranlar: {
    kicker: "Sube Katmani",
    title: "Sube ve fiyat modeli kararlari daha net okunuyor",
    description:
      "Restoran kartlari, aktiflik ve fiyat yapilari operasyonla daha bagli bir yuzeyde incelenebiliyor.",
    relatedLabels: ["Puantaj", "Satış", "Personel"],
  },
  Raporlar: {
    kicker: "Karar Paneli",
    title: "Ciro, maliyet ve trend dili burada toparlaniyor",
    description:
      "Aylik resmi daha premium bir rapor deneyimine cekiyor; ticari ve operasyonel etkileri tek bakista okumayi kolaylastiriyor.",
    relatedLabels: ["Aylık Hakediş", "Satış", "Satın Alma"],
  },
  "Sistem Kayıtları": {
    kicker: "Admin Katmani",
    title: "Kim ne yapti sorusuna daha temiz cevap",
    description:
      "Audit akisinda filtreleme, akis takibi ve operasyonel seffaflik ayni estetik kabukta.",
    relatedLabels: ["Ekipman", "Profil", "Genel Bakış"],
  },
  Profil: {
    kicker: "Kimlik Katmani",
    title: "Profil ve sifre akisi de preview deneyimine dahil",
    description:
      "Sadece operasyon degil, kullanicinin uygulama ile kurdugu kisiel temas da yeni dilde gorunur halde.",
    relatedLabels: ["Genel Bakış", "Sistem Kayıtları"],
  },
};

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
  const previewMode = isPreviewPathname(pathname);

  const visibleItems = useMemo(() => {
    if (previewMode) {
      const previewItemMap: Record<string, string> = {
        "/": "/preview",
        "/attendance": "/preview/attendance",
        "/personnel": "/preview/personnel",
        "/deductions": "/preview/deductions",
        "/equipment": "/preview/equipment",
        "/payroll": "/preview/payroll",
        "/purchases": "/preview/purchases",
        "/sales": "/preview/sales",
        "/restaurants": "/preview/restaurants",
        "/reports": "/preview/reports",
        "/audit": "/preview/audit",
        "/account": "/preview/account",
      };
      return sidebarItems
        .filter(
          (item) =>
            item.label === "Genel Bakış" ||
            item.label === "Puantaj" ||
            item.label === "Personel" ||
            item.label === "Sistem Kayıtları" ||
            item.label === "Kesintiler" ||
            item.label === "Ekipman" ||
            item.label === "Aylık Hakediş" ||
            item.label === "Satın Alma" ||
            item.label === "Satış" ||
            item.label === "Restoranlar" ||
            item.label === "Raporlar" ||
            item.label === "Profil",
        )
        .map(
          (item): SidebarItem => ({
            ...item,
            href: previewItemMap[item.href] ?? "/preview",
          }),
        );
    }
    return filterSidebarItems(user?.allowed_actions ?? []);
  }, [previewMode, user?.allowed_actions]);
  const canViewActiveItem = useMemo(
    () => visibleItems.some((item) => item.label === activeItem),
    [visibleItems, activeItem],
  );
  const previewMeta = previewMetaByLabel[activeItem] ?? previewMetaByLabel["Genel Bakış"];
  const previewRelatedItems = useMemo(
    () =>
      previewMeta.relatedLabels
        .map((label) => visibleItems.find((item) => item.label === label))
        .filter(Boolean) as SidebarItem[],
    [previewMeta.relatedLabels, visibleItems],
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
    if (user.must_change_password && pathname !== "/account") {
      router.replace("/account");
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
          <h2 style={{ margin: "18px 0 10px" }}>v2 oturumu aciliyor</h2>
          <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
            Yetki ve oturum bilgileri kontrol ediliyor. Hazir oldugunda seni dogrudan ilgili module alacagiz.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside
        className="app-shell__sidebar"
        style={{
          padding: "28px 24px 24px",
          borderRight: "1px solid rgba(255, 255, 255, 0.08)",
          background:
            "linear-gradient(180deg, rgba(19, 32, 48, 0.98) 0%, rgba(24, 40, 59, 0.96) 42%, rgba(37, 55, 77, 0.96) 100%)",
          color: "#f6efe3",
          backdropFilter: "blur(18px)",
          boxShadow: "inset -1px 0 0 rgba(255, 255, 255, 0.06)",
        }}
      >
        <div
          style={{
            padding: "18px 18px 16px",
            borderRadius: "28px",
            background: "linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))",
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow: "0 20px 38px rgba(0, 0, 0, 0.18)",
          }}
        >
          <div
            style={{
              display: "inline-flex",
              padding: "6px 10px",
              borderRadius: "999px",
              background: "rgba(185, 116, 41, 0.18)",
              color: "#f1c28f",
              fontSize: "0.72rem",
              fontWeight: 800,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            {previewMode ? "v2 Preview" : "v2 Pilot"}
          </div>
          <div
            style={{
              marginTop: "16px",
              color: "#fff7ed",
              fontWeight: 900,
              fontSize: "1.85rem",
              letterSpacing: "-0.03em",
              lineHeight: 0.95,
              fontFamily:
                '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
            }}
          >
            Cat Kapinda CRM
          </div>
          <div
            style={{
              marginTop: "10px",
              color: "rgba(246, 239, 227, 0.72)",
              fontSize: "0.92rem",
              lineHeight: 1.6,
            }}
          >
            Operasyonun gunluk nabzi, karar panelleri ve saha akisi tek kabukta.
          </div>
        </div>
        {previewMode ? (
          <div
            style={{
              padding: "14px 16px",
              borderRadius: "22px",
              border: "1px solid rgba(241,194,143,0.14)",
              background: "rgba(185, 116, 41, 0.08)",
              color: "#f8e2c0",
              lineHeight: 1.6,
              fontSize: "0.9rem",
            }}
          >
            Preview modundayiz. Bu hat backend beklemeden tasarim yuzeylerini gezmek icin acik.
          </div>
        ) : null}
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
                borderRadius: "20px",
                border:
                  item.label === activeItem
                    ? "1px solid rgba(241, 194, 143, 0.4)"
                    : "1px solid rgba(255, 255, 255, 0.08)",
                background:
                  item.label === activeItem
                    ? "linear-gradient(135deg, rgba(185, 116, 41, 0.24), rgba(255,255,255,0.08))"
                    : "rgba(255, 255, 255, 0.03)",
                color: item.label === activeItem ? "#fff4e5" : "rgba(246, 239, 227, 0.84)",
                fontWeight: item.label === activeItem ? 800 : 700,
                boxShadow:
                  item.label === activeItem ? "0 18px 34px rgba(0, 0, 0, 0.16)" : "none",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "12px",
                }}
              >
                <span>{item.label}</span>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minWidth: "30px",
                    height: "30px",
                    borderRadius: "12px",
                    background:
                      item.label === activeItem
                        ? "rgba(255,255,255,0.14)"
                        : "rgba(255,255,255,0.06)",
                    fontSize: "0.76rem",
                    fontWeight: 900,
                  }}
                >
                  {item.label.charAt(0)}
                </span>
              </div>
            </Link>
          ))}
        </nav>

        <div
          style={{
            marginTop: "auto",
            paddingTop: "10px",
            display: "grid",
            gap: "10px",
          }}
        >
          <div
            style={{
              padding: "16px",
              borderRadius: "22px",
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255, 255, 255, 0.05)",
            }}
          >
            <div
              style={{
                fontWeight: 800,
                color: "#fff7ed",
              }}
            >
              {user.full_name}
            </div>
            <div
              style={{
                marginTop: "4px",
                color: "rgba(246, 239, 227, 0.66)",
                fontSize: "0.9rem",
              }}
            >
              {user.role_display}
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              void logout().then(() => router.replace("/login"));
            }}
            style={{
              padding: "13px 16px",
              borderRadius: "18px",
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255, 255, 255, 0.04)",
              color: "#fff4e5",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Oturumu Kapat
          </button>
        </div>
      </aside>
      <main
        className="app-shell__main"
        style={{
          padding: "30px",
        }}
      >
        <div
          style={{
            display: "grid",
            gap: "22px",
          }}
        >
          {previewMode ? (
            <section
              style={{
                padding: "22px 24px",
                borderRadius: "28px",
                border: "1px solid var(--line)",
                background:
                  "linear-gradient(180deg, rgba(255,253,248,0.98), rgba(246,240,229,0.96))",
                boxShadow: "var(--shadow-soft)",
                display: "grid",
                gap: "16px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: "16px",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "grid", gap: "8px", maxWidth: "72ch" }}>
                  <div
                    style={{
                      display: "inline-flex",
                      width: "fit-content",
                      padding: "6px 10px",
                      borderRadius: "999px",
                      background: "rgba(185,116,41,0.12)",
                      color: "var(--accent-strong)",
                      fontSize: "0.74rem",
                      fontWeight: 800,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    {previewMeta.kicker}
                  </div>
                  <h1
                    style={{
                      margin: 0,
                      fontFamily:
                        '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
                      fontSize: "clamp(1.8rem, 4vw, 2.8rem)",
                      lineHeight: 0.95,
                      letterSpacing: "-0.04em",
                    }}
                  >
                    {previewMeta.title}
                  </h1>
                  <p
                    style={{
                      margin: 0,
                      color: "var(--muted)",
                      lineHeight: 1.75,
                      fontSize: "0.97rem",
                    }}
                  >
                    {previewMeta.description}
                  </p>
                </div>

                <div
                  style={{
                    display: "grid",
                    gap: "10px",
                    minWidth: "260px",
                  }}
                >
                  <Link
                    href="/preview"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "12px",
                      padding: "12px 14px",
                      borderRadius: "18px",
                      background: "var(--surface-ink)",
                      color: "#fff7ea",
                      fontWeight: 800,
                      boxShadow: "var(--shadow-deep)",
                    }}
                  >
                    <span>Preview Hub'a Don</span>
                    <span
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "999px",
                        display: "grid",
                        placeItems: "center",
                        background: "rgba(255,255,255,0.08)",
                      }}
                    >
                      H
                    </span>
                  </Link>
                  <div
                    style={{
                      display: "grid",
                      gap: "8px",
                    }}
                  >
                    <div
                      style={{
                        color: "var(--muted)",
                        fontSize: "0.74rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Ilgili Gecisler
                    </div>
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "8px",
                      }}
                    >
                      {previewRelatedItems.map((item) => (
                        <Link
                          key={item.label}
                          href={item.href}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "8px",
                            padding: "10px 12px",
                            borderRadius: "14px",
                            background: "rgba(24,40,59,0.06)",
                            border: "1px solid rgba(24,40,59,0.08)",
                            color: "var(--text)",
                            fontWeight: 700,
                            fontSize: "0.9rem",
                          }}
                        >
                          <span>{item.label}</span>
                          <span
                            style={{
                              width: "22px",
                              height: "22px",
                              borderRadius: "999px",
                              display: "grid",
                              placeItems: "center",
                              background: "rgba(185,116,41,0.12)",
                              color: "var(--accent-strong)",
                              fontSize: "0.72rem",
                              fontWeight: 900,
                            }}
                          >
                            {item.label.charAt(0)}
                          </span>
                        </Link>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(15,95,215,0.08)",
                    color: "#0f5fd7",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Backend bagimsiz preview akisi acik
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(185,116,41,0.1)",
                    color: "var(--accent-strong)",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Mock veri ile gezilebilir durum
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(24,40,59,0.08)",
                    color: "var(--text)",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Aktif sayfa: {activeItem}
                </span>
              </div>
            </section>
          ) : null}

          {children}
        </div>
      </main>
    </div>
  );
}
