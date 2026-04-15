"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type PreviewDashboard = {
  module: string;
  status: string;
  hero: {
    active_restaurants: number;
    active_personnel: number;
    month_attendance_entries: number;
    month_deduction_entries: number;
  };
  modules: Array<{
    key: string;
    title: string;
    description: string;
    href: string;
    primary_label: string;
    primary_value: string;
    secondary_label: string;
    secondary_value: string;
  }>;
  recent_activity: Array<{
    module_key: string;
    module_label: string;
    title: string;
    subtitle: string;
    meta: string;
    entry_date: string | null;
    href: string;
  }>;
};

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

function heroMetric(label: string, value: string, note: string) {
  return (
    <article
      key={label}
      style={{
        padding: "18px 18px 16px",
        borderRadius: "22px",
        border: "1px solid rgba(255,255,255,0.1)",
        background: "rgba(255,255,255,0.06)",
        display: "grid",
        gap: "8px",
      }}
    >
      <div
        style={{
          color: "rgba(255,247,234,0.72)",
          fontSize: "0.72rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {label}
      </div>
      <div
        style={{
          ...serifStyle,
          fontSize: "2rem",
          lineHeight: 0.95,
          fontWeight: 700,
          color: "#fff7ea",
        }}
      >
        {value}
      </div>
      <div
        style={{
          color: "rgba(255,247,234,0.72)",
          fontSize: "0.9rem",
          lineHeight: 1.55,
        }}
      >
        {note}
      </div>
    </article>
  );
}

function moduleTile(
  item: PreviewDashboard["modules"][number],
  accent: "ink" | "paper" = "paper",
) {
  return (
    <Link
      key={item.key}
      href={item.href}
      style={{
        display: "grid",
        gap: "14px",
        padding: "20px",
        borderRadius: "24px",
        border:
          accent === "ink"
            ? "1px solid rgba(255,255,255,0.08)"
            : "1px solid var(--line)",
        background:
          accent === "ink"
            ? "linear-gradient(180deg, rgba(24,40,59,0.94), rgba(31,48,69,0.94))"
            : "linear-gradient(180deg, rgba(255,253,248,0.98), rgba(247,241,231,0.96))",
        color: accent === "ink" ? "#fff7ea" : "var(--text)",
        boxShadow: accent === "ink" ? "var(--shadow-deep)" : "var(--shadow-soft)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "16px",
        }}
      >
        <div style={{ display: "grid", gap: "8px" }}>
          <div
            style={{
              ...serifStyle,
              fontSize: "1.45rem",
              lineHeight: 0.98,
              fontWeight: 700,
            }}
          >
            {item.title}
          </div>
          <p
            style={{
              margin: 0,
              color: accent === "ink" ? "rgba(255,247,234,0.7)" : "var(--muted)",
              fontSize: "0.94rem",
              lineHeight: 1.65,
            }}
          >
            {item.description}
          </p>
        </div>
        <div
          style={{
            minWidth: "42px",
            height: "42px",
            borderRadius: "14px",
            display: "grid",
            placeItems: "center",
            background:
              accent === "ink" ? "rgba(255,255,255,0.08)" : "rgba(24,40,59,0.08)",
            fontWeight: 900,
          }}
        >
          {item.title.charAt(0)}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: "10px",
        }}
      >
        <div
          style={{
            padding: "12px 12px 10px",
            borderRadius: "16px",
            background:
              accent === "ink" ? "rgba(255,255,255,0.06)" : "rgba(24,40,59,0.05)",
          }}
        >
          <div
            style={{
              fontSize: "0.72rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: accent === "ink" ? "rgba(255,247,234,0.64)" : "var(--muted)",
            }}
          >
            {item.primary_label}
          </div>
          <div style={{ marginTop: "7px", fontSize: "1.15rem", fontWeight: 900 }}>
            {item.primary_value}
          </div>
        </div>
        <div
          style={{
            padding: "12px 12px 10px",
            borderRadius: "16px",
            background:
              accent === "ink" ? "rgba(185,116,41,0.12)" : "rgba(185,116,41,0.08)",
          }}
        >
          <div
            style={{
              fontSize: "0.72rem",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: accent === "ink" ? "rgba(255,247,234,0.64)" : "var(--muted)",
            }}
          >
            {item.secondary_label}
          </div>
          <div style={{ marginTop: "7px", fontSize: "1.15rem", fontWeight: 900 }}>
            {item.secondary_value}
          </div>
        </div>
      </div>
    </Link>
  );
}

function signalCard(item: PreviewDashboard["recent_activity"][number]) {
  return (
    <Link
      key={`${item.module_key}-${item.title}-${item.entry_date}`}
      href={item.href}
      style={{
        display: "grid",
        gap: "8px",
        padding: "16px 18px",
        borderRadius: "20px",
        border: "1px solid var(--line)",
        background: "rgba(255,255,255,0.84)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "12px",
          alignItems: "center",
        }}
      >
        <span
          style={{
            display: "inline-flex",
            padding: "6px 10px",
            borderRadius: "999px",
            background: "rgba(185,116,41,0.12)",
            color: "var(--accent-strong)",
            fontSize: "0.74rem",
            fontWeight: 800,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
          }}
        >
          {item.module_label}
        </span>
        <span style={{ color: "var(--muted)", fontSize: "0.86rem" }}>
          {item.entry_date || "Takvim yok"}
        </span>
      </div>
      <div
        style={{
          ...serifStyle,
          fontSize: "1.22rem",
          lineHeight: 1.02,
          fontWeight: 700,
        }}
      >
        {item.title}
      </div>
      <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.93rem" }}>
        {item.subtitle}
      </div>
      <div style={{ fontWeight: 800, fontSize: "0.92rem" }}>{item.meta}</div>
    </Link>
  );
}

export default function PreviewOverviewPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<PreviewDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      if (loading) {
        return;
      }
      if (!user) {
        if (active) {
          setDashboard(null);
          setDashboardLoading(false);
        }
        return;
      }

      setDashboardLoading(true);
      try {
        const response = await apiFetch("/overview/dashboard");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as PreviewDashboard;
        if (active) {
          setDashboard(payload);
        }
      } catch {
        if (active) {
          setDashboard(null);
        }
      } finally {
        if (active) {
          setDashboardLoading(false);
        }
      }
    }

    void loadDashboard();
    return () => {
      active = false;
    };
  }, [loading, user]);

  const moduleMap = useMemo(() => {
    const map = new Map<string, PreviewDashboard["modules"][number]>();
    for (const item of dashboard?.modules ?? []) {
      map.set(item.key, item);
    }
    return map;
  }, [dashboard?.modules]);

  const fieldOps = useMemo(
    () =>
      ["attendance", "personnel", "deductions", "restaurants", "equipment"]
        .map((key) => moduleMap.get(key))
        .filter(Boolean) as PreviewDashboard["modules"],
    [moduleMap],
  );

  const businessOps = useMemo(
    () =>
      ["sales", "purchases", "payroll", "reports"]
        .map((key) => moduleMap.get(key))
        .filter(Boolean) as PreviewDashboard["modules"],
    [moduleMap],
  );

  const controlOps = useMemo(
    () =>
      ["audit"]
        .map((key) => moduleMap.get(key))
        .filter(Boolean) as PreviewDashboard["modules"],
    [moduleMap],
  );

  return (
    <AppShell activeItem="Genel Bakış">
      <section
        style={{
          display: "grid",
          gap: "22px",
        }}
      >
        <section
          style={{
            padding: "30px",
            borderRadius: "34px",
            background:
              "linear-gradient(145deg, rgba(22, 38, 58, 0.98), rgba(37, 56, 79, 0.96))",
            color: "#fff7ea",
            boxShadow: "var(--shadow-deep)",
            position: "relative",
            overflow: "hidden",
            display: "grid",
            gap: "22px",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: "auto -90px -110px auto",
              width: "260px",
              height: "260px",
              borderRadius: "999px",
              background: "radial-gradient(circle, rgba(185,116,41,0.32), transparent 72%)",
            }}
          />
          <div
            style={{
              display: "inline-flex",
              width: "fit-content",
              padding: "7px 12px",
              borderRadius: "999px",
              background: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.12)",
              color: "#f5d7b1",
              fontSize: "0.74rem",
              fontWeight: 800,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            v2 Preview Atlas
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.25fr) minmax(320px, 0.75fr)",
              gap: "18px",
              alignItems: "start",
            }}
          >
            <div style={{ display: "grid", gap: "16px" }}>
              <h1
                style={{
                  ...serifStyle,
                  margin: 0,
                  fontSize: "clamp(2.8rem, 6vw, 5rem)",
                  lineHeight: 0.9,
                  fontWeight: 700,
                  maxWidth: "10ch",
                }}
              >
                Yeni arayüzü akış akış gezmek için hazırladık.
              </h1>
              <p
                style={{
                  margin: 0,
                  maxWidth: "72ch",
                  color: "rgba(255,247,234,0.76)",
                  fontSize: "1rem",
                  lineHeight: 1.8,
                }}
              >
                Bu preview hattı artık sadece birkaç mock kart göstermiyor. Operasyon, ticari yüzeyler,
                backoffice ve admin katmanı tek kabukta gezilebilir durumda. Buradan herhangi bir modüle
                girip tasarım dilini gerçek kullanım hissiyle inceleyebilirsin.
              </p>
            </div>

            <div
              style={{
                padding: "20px",
                borderRadius: "24px",
                border: "1px solid rgba(255,255,255,0.08)",
                background: "rgba(255,255,255,0.05)",
                display: "grid",
                gap: "12px",
              }}
            >
              <div
                style={{
                  fontSize: "0.74rem",
                  fontWeight: 800,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "rgba(255,247,234,0.72)",
                }}
              >
                Preview Durumu
              </div>
              <div
                style={{
                  ...serifStyle,
                  fontSize: "2rem",
                  lineHeight: 0.92,
                  fontWeight: 700,
                }}
              >
                {dashboardLoading ? "Hazırlanıyor" : "Gezilebilir Yüzey Açık"}
              </div>
              <div
                style={{
                  color: "rgba(255,247,234,0.72)",
                  lineHeight: 1.7,
                }}
              >
                {dashboardLoading
                  ? "Dashboard verisi yükleniyor."
                  : `${dashboard?.modules.length ?? 0} modül ve ${dashboard?.recent_activity.length ?? 0} canlı sinyal preview akışına bağlı.`}
              </div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
              gap: "12px",
            }}
          >
            {heroMetric("Aktif Şube", String(dashboard?.hero.active_restaurants ?? 0), "Saha tarafında görünen restoran yoğunluğu")}
            {heroMetric("Aktif Kadro", String(dashboard?.hero.active_personnel ?? 0), "Preview üzerinde dağılmış operasyon ekibi")}
            {heroMetric("Aylık Puantaj", String(dashboard?.hero.month_attendance_entries ?? 0), "Attendance akışındaki Nisan kayıtları")}
            {heroMetric("Aylık Kesinti", String(dashboard?.hero.month_deduction_entries ?? 0), "Bordro ve kesinti yüzeyine bağlı kayıtlar")}
          </div>
        </section>

        {!dashboard && !dashboardLoading ? (
          <section
            style={{
              padding: "18px 20px",
              borderRadius: "24px",
              border: "1px dashed rgba(15, 95, 215, 0.32)",
              background: "rgba(255,255,255,0.7)",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Preview dashboard verisi şu anda alınamadı. Bu sayfa veri geldiğinde modülleri akış bazlı kümeler halinde gösterecek.
          </section>
        ) : null}

        {dashboard ? (
          <>
            <section style={{ display: "grid", gap: "14px" }}>
              <div style={{ display: "grid", gap: "6px" }}>
                <div
                  style={{
                    color: "var(--accent-strong)",
                    fontWeight: 800,
                    fontSize: "0.76rem",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                  }}
                >
                  Saha Omurgası
                </div>
                <h2 style={{ ...serifStyle, margin: 0, fontSize: "2rem", lineHeight: 0.96 }}>
                  Operasyonun günlük kasları
                </h2>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: "14px",
                }}
              >
                {fieldOps.map((item, index) => moduleTile(item, index === 0 ? "ink" : "paper"))}
              </div>
            </section>

            <section style={{ display: "grid", gap: "14px" }}>
              <div style={{ display: "grid", gap: "6px" }}>
                <div
                  style={{
                    color: "var(--accent-strong)",
                    fontWeight: 800,
                    fontSize: "0.76rem",
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                  }}
                >
                  Ticari ve Finansal Hat
                </div>
                <h2 style={{ ...serifStyle, margin: 0, fontSize: "2rem", lineHeight: 0.96 }}>
                  Karar, maliyet ve büyüme yüzeyleri
                </h2>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: "14px",
                }}
              >
                {businessOps.map((item, index) => moduleTile(item, index === 0 ? "ink" : "paper"))}
              </div>
            </section>

            <section
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.45fr) minmax(320px, 0.55fr)",
                gap: "16px",
                alignItems: "start",
              }}
            >
              <div style={{ display: "grid", gap: "14px" }}>
                <div style={{ display: "grid", gap: "6px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.76rem",
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    Anlık Sinyaller
                  </div>
                  <h2 style={{ ...serifStyle, margin: 0, fontSize: "2rem", lineHeight: 0.96 }}>
                    Preview içinde dolaşırken nereden başlamalı?
                  </h2>
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                    gap: "12px",
                  }}
                >
                  {dashboard.recent_activity.map(signalCard)}
                </div>
              </div>

              <aside
                style={{
                  display: "grid",
                  gap: "14px",
                  padding: "20px",
                  borderRadius: "24px",
                  border: "1px solid var(--line)",
                  background: "linear-gradient(180deg, rgba(255,253,248,0.98), rgba(247,241,231,0.96))",
                  boxShadow: "var(--shadow-soft)",
                }}
              >
                <div style={{ display: "grid", gap: "6px" }}>
                  <div
                    style={{
                      color: "var(--accent-strong)",
                      fontWeight: 800,
                      fontSize: "0.76rem",
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    Kontrol Katmanı
                  </div>
                  <h3 style={{ ...serifStyle, margin: 0, fontSize: "1.7rem", lineHeight: 0.96 }}>
                    Admin ve profil yüzeyleri
                  </h3>
                  <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
                    Denetim akışı ve hesap yüzeyi de preview hattının parçası. Böylece yalnızca saha değil, yönetim dilini de aynı estetikte görebilirsin.
                  </p>
                </div>
                <div style={{ display: "grid", gap: "12px" }}>
                  {controlOps.map((item) => moduleTile(item))}
                  <Link
                    href="/preview/account"
                    style={{
                      display: "grid",
                      gap: "10px",
                      padding: "18px",
                      borderRadius: "20px",
                      border: "1px solid var(--line)",
                      background: "rgba(255,255,255,0.84)",
                    }}
                  >
                    <div style={{ ...serifStyle, fontSize: "1.25rem", lineHeight: 0.98, fontWeight: 700 }}>
                      Profil
                    </div>
                    <div style={{ color: "var(--muted)", lineHeight: 1.65 }}>
                      Şifre akışı, kimlik hissi ve kişisel ayar yüzeyini preview içinde ayrıca inceleyebilirsin.
                    </div>
                  </Link>
                </div>
              </aside>
            </section>
          </>
        ) : null}
      </section>
    </AppShell>
  );
}
