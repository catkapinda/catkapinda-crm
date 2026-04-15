"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "../../components/auth/auth-provider";
import { AuditManagementWorkspace } from "../../components/audit/audit-management-workspace";
import { AppShell } from "../../components/shell/app-shell";
import { apiFetch } from "../../lib/api";

type AuditDashboard = {
  module: string;
  status: string;
  summary: {
    total_entries: number;
    last_7_days: number;
    unique_actors: number;
    unique_entities: number;
  };
  recent_entries: Array<{
    id: number;
    created_at: string;
    actor_username: string;
    actor_full_name: string;
    actor_role: string;
    entity_type: string;
    entity_id: string;
    action_type: string;
    summary: string;
    details_json: string;
  }>;
  action_options: string[];
  entity_options: string[];
  actor_options: string[];
};

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

function metricCard(label: string, value: string, note: string, tone: "accent" | "soft" = "soft") {
  return (
    <article
      key={label}
      style={{
        padding: "18px 18px 16px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background:
          tone === "accent"
            ? "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(246,239,228,0.96))"
            : "var(--surface-strong)",
        boxShadow: "0 18px 42px rgba(20, 39, 67, 0.06)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.78rem",
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div
        style={{
          ...serifStyle,
          marginTop: "10px",
          fontSize: "2rem",
          lineHeight: 0.95,
          fontWeight: 700,
        }}
      >
        {value}
      </div>
      <div
        style={{
          marginTop: "8px",
          color: "var(--muted)",
          lineHeight: 1.6,
          fontSize: "0.92rem",
        }}
      >
        {note}
      </div>
    </article>
  );
}

function narrativeCard({
  eyebrow,
  title,
  body,
  tone = "paper",
}: {
  eyebrow: string;
  title: string;
  body: string;
  tone?: "paper" | "ink" | "accent";
}) {
  const palette =
    tone === "ink"
      ? {
          background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
          border: "1px solid rgba(255,255,255,0.08)",
          title: "#fff7ea",
          body: "rgba(255,247,234,0.72)",
          eyebrow: "rgba(255,247,234,0.62)",
        }
      : tone === "accent"
        ? {
            background: "linear-gradient(180deg, rgba(185,116,41,0.12), rgba(255,248,236,0.98))",
            border: "1px solid rgba(185,116,41,0.18)",
            title: "var(--text)",
            body: "var(--muted)",
            eyebrow: "var(--accent-strong)",
          }
        : {
            background: "rgba(255,255,255,0.84)",
            border: "1px solid var(--line)",
            title: "var(--text)",
            body: "var(--muted)",
            eyebrow: "var(--muted)",
          };

  return (
    <article
      style={{
        padding: "18px 18px 16px",
        borderRadius: "22px",
        background: palette.background,
        border: palette.border,
        boxShadow: tone === "ink" ? "var(--shadow-deep)" : "var(--shadow-soft)",
        display: "grid",
        gap: "10px",
      }}
    >
      <div
        style={{
          color: palette.eyebrow,
          fontSize: "0.74rem",
          fontWeight: 800,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
        }}
      >
        {eyebrow}
      </div>
      <div
        style={{
          ...serifStyle,
          color: palette.title,
          fontSize: "1.45rem",
          lineHeight: 0.98,
          fontWeight: 700,
        }}
      >
        {title}
      </div>
      <div
        style={{
          color: palette.body,
          fontSize: "0.93rem",
          lineHeight: 1.65,
        }}
      >
        {body}
      </div>
    </article>
  );
}

function listCard(
  title: string,
  subtitle: string,
  items: Array<{ title: string; meta: string; value: string }>,
) {
  return (
    <section
      style={{
        display: "grid",
        gap: "12px",
        padding: "20px",
        borderRadius: "22px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
        boxShadow: "0 18px 42px rgba(20, 39, 67, 0.06)",
      }}
    >
      <div>
        <h2 style={{ margin: 0, fontSize: "1.08rem" }}>{title}</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>{subtitle}</p>
      </div>
      <div
        style={{
          display: "grid",
          gap: "10px",
          maxHeight: "280px",
          overflow: "auto",
          paddingRight: "4px",
        }}
      >
        {items.length ? (
          items.map((item, index) => (
            <article
              key={`${title}-${index}-${item.title}`}
              style={{
                display: "grid",
                gap: "6px",
                padding: "14px 16px",
                borderRadius: "18px",
                border: "1px solid var(--line)",
                background: "rgba(255, 255, 255, 0.88)",
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
                <strong>{item.title}</strong>
                <span style={{ color: "var(--muted)", fontSize: "0.88rem" }}>{item.value}</span>
              </div>
              <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>{item.meta}</div>
            </article>
          ))
        ) : (
          <div
            style={{
              padding: "18px",
              borderRadius: "16px",
              border: "1px dashed rgba(15, 95, 215, 0.25)",
              color: "var(--muted)",
              background: "rgba(255, 255, 255, 0.72)",
            }}
          >
            Henüz kayıt yok.
          </div>
        )}
      </div>
    </section>
  );
}

function formatTimestamp(value: string) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function formatActor(entry: AuditDashboard["recent_entries"][number]) {
  return entry.actor_full_name || entry.actor_username || "Bilinmeyen kullanıcı";
}

function countEntries(values: string[]) {
  const counts = new Map<string, number>();
  values.forEach((value) => {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  });
  return [...counts.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "tr"));
}

export default function AuditPage() {
  const { user, loading } = useAuth();
  const [dashboard, setDashboard] = useState<AuditDashboard | null>(null);
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
        const response = await apiFetch("/audit/dashboard?limit=12");
        if (!response.ok) {
          if (active) {
            setDashboard(null);
          }
          return;
        }
        const payload = (await response.json()) as AuditDashboard;
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

  const decisionDeck = useMemo(() => {
    if (!dashboard) {
      return [];
    }

    const topEntry = dashboard.recent_entries[0] ?? null;
    const actionMix = countEntries(dashboard.recent_entries.map((entry) => entry.action_type));
    const entityMix = countEntries(dashboard.recent_entries.map((entry) => entry.entity_type));
    const dominantAction = actionMix[0] ?? null;
    const dominantEntity = entityMix[0] ?? null;
    const recentPressure =
      dashboard.summary.last_7_days >= Math.max(8, Math.ceil(dashboard.summary.total_entries * 0.3));
    const actorSpreadWide =
      dashboard.summary.unique_actors >= Math.max(4, Math.ceil(dashboard.summary.unique_entities * 0.8));

    return [
      {
        eyebrow: "Kayıt Nabzi",
        title: recentPressure ? "Son 7 gün daha hızlı akiyor." : "Kayıt ritmi kontrollü görünüyor.",
        body: `${dashboard.summary.last_7_days} kayıt son 7 gunde olustu. Toplam ${dashboard.summary.total_entries} kayıt içinde bu ritim, sistemde degisimin ne kadar taze oldugunu hizla anlatır.`,
        tone: recentPressure ? "ink" : "paper",
      },
      {
        eyebrow: "En Sıcak Aksiyon",
        title: topEntry
          ? `${topEntry.action_type} · ${topEntry.entity_type}`
          : "Aksiyon sinyali henüz yok.",
        body: topEntry
          ? `${formatActor(topEntry)} tarafindan ${formatTimestamp(topEntry.created_at)} aninda tetiklendi. ${topEntry.summary || "Bu hareket detay akışı içinde ilk okunacak olaylardan biri."}`
          : "Yeni audit hareketleri geldikçe burada ilk dikkat isteyen aksiyon görünecek.",
        tone: "paper",
      },
      {
        eyebrow: actorSpreadWide ? "Oyuncu Dagilimi" : "Varlık Baskisi",
        title: actorSpreadWide
          ? "Kayıt izi ekibe yayiliyor."
          : dominantEntity
            ? `${dominantEntity[0]} önde gidiyor.`
            : "Dagilim sinyali henüz yok.",
        body: actorSpreadWide
          ? `${dashboard.summary.unique_actors} farklı kullanıcı ve ${dashboard.summary.unique_entities} farklı varlık izleniyor. Bu dağılım, denetim akışının tek kişiye bağlı kalmadığını gösterir.`
          : dominantEntity
            ? `${dominantEntity[0]} tarafında ${dominantEntity[1]} hareket goruluyor. ${dominantAction ? `${dominantAction[0]} aksiyonu ${dominantAction[1]} kez tekrar etti.` : "Aksiyon dağılımı burada yogunlasiyor."}`
            : "Aksiyon ve varlık karmasi geldikçe burada baskı noktasi öne cikacak.",
        tone: actorSpreadWide ? "accent" : "paper",
      },
    ] as const;
  }, [dashboard]);

  const actionMix = useMemo(() => {
    if (!dashboard) {
      return [];
    }
    return countEntries(dashboard.recent_entries.map((entry) => entry.action_type)).slice(0, 6);
  }, [dashboard]);

  const entityMix = useMemo(() => {
    if (!dashboard) {
      return [];
    }
    return countEntries(dashboard.recent_entries.map((entry) => entry.entity_type)).slice(0, 6);
  }, [dashboard]);

  return (
    <AppShell activeItem="Sistem Kayıtları">
      <section
        style={{
          display: "grid",
          gap: "18px",
        }}
      >
        <div
          style={{
            padding: "28px",
            borderRadius: "30px",
            background: "linear-gradient(180deg, rgba(255,252,246,0.98), rgba(248,242,233,0.96))",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
            display: "grid",
            gap: "18px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.35fr) minmax(280px, 0.9fr)",
              gap: "18px",
              alignItems: "stretch",
            }}
          >
            <div
              style={{
                display: "grid",
                gap: "16px",
                alignContent: "start",
              }}
            >
              <div
                style={{
                  display: "inline-flex",
                  width: "fit-content",
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
                Audit Control
              </div>
              <div style={{ display: "grid", gap: "10px", maxWidth: "72ch" }}>
                <h1
                  style={{
                    ...serifStyle,
                    margin: 0,
                    fontSize: "clamp(2.2rem, 4vw, 3.6rem)",
                    lineHeight: 0.96,
                    fontWeight: 700,
                  }}
                >
                  Sistem hareketini sadece kayıt olarak değil, operasyon izi olarak okuyoruz.
                </h1>
                <p
                  style={{
                    margin: 0,
                    maxWidth: "74ch",
                    color: "var(--muted)",
                    lineHeight: 1.76,
                    fontSize: "1.02rem",
                  }}
                >
                  Kim, neyi, hangi ritimde değiştiriyor sorusunu daha okunur bir karar katmanina
                  taşıyoruz. Hedefimiz, denetim hattini sadece arama masasi değil; erken sinyal
                  ve güven katmanı gibi hissettirmek.
                </p>
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
                  Kim / ne / ne zaman aynı hatta
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
                  Aksiyon ve varlık baskısı görünür
                </span>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gap: "12px",
              }}
            >
              <article
                style={{
                  padding: "18px 18px 16px",
                  borderRadius: "24px",
                  background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
                  color: "#fff7ea",
                  boxShadow: "var(--shadow-deep)",
                  display: "grid",
                  gap: "14px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "12px",
                    alignItems: "start",
                    flexWrap: "wrap",
                  }}
                >
                  <div style={{ display: "grid", gap: "6px" }}>
                    <div
                      style={{
                        color: "rgba(255,247,234,0.62)",
                        fontSize: "0.74rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Akim Nabzi
                    </div>
                    <div
                      style={{
                        ...serifStyle,
                        fontSize: "1.8rem",
                        lineHeight: 0.96,
                        fontWeight: 700,
                      }}
                    >
                      {dashboard?.summary.last_7_days ?? 0} son 7 gün hareketi
                    </div>
                  </div>
                  <div
                    style={{
                      display: "inline-flex",
                      padding: "7px 10px",
                      borderRadius: "999px",
                      background: "rgba(255,255,255,0.08)",
                      color: "rgba(255,247,234,0.82)",
                      fontSize: "0.8rem",
                      fontWeight: 800,
                    }}
                  >
                    Audit Room
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
                      background: "rgba(255,255,255,0.06)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.72rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Kullanıcı
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.unique_actors ?? 0}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "12px 12px 10px",
                      borderRadius: "16px",
                      background: "rgba(185,116,41,0.14)",
                    }}
                  >
                    <div
                      style={{
                        color: "rgba(255,247,234,0.64)",
                        fontSize: "0.72rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      Varlık
                    </div>
                    <div style={{ marginTop: "8px", fontSize: "1.05rem", fontWeight: 900 }}>
                      {dashboard?.summary.unique_entities ?? 0}
                    </div>
                  </div>
                </div>
              </article>

              <article
                style={{
                  padding: "16px 18px",
                  borderRadius: "22px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.78)",
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
                  Okuma Notu
                </div>
                <div
                  style={{
                    color: "var(--text)",
                    fontSize: "0.95rem",
                    lineHeight: 1.7,
                  }}
                >
                  Bu ekranda önce son 7 gün ritmine, sonra aksiyon dagilimina ve en son tekil
                  varlık baskısına bakmak, hangi modülde yakından izleme gerektiğini daha hızlı
                  hissettirir.
                </div>
              </article>
            </div>
          </div>
        </div>

        {dashboardLoading ? (
          <div
            style={{
              padding: "18px 20px",
              borderRadius: "22px",
              border: "1px solid rgba(15, 95, 215, 0.14)",
              background: "rgba(15, 95, 215, 0.06)",
              color: "var(--muted)",
            }}
          >
            Sistem kayıtları yükleniyor...
          </div>
        ) : !dashboard ? (
          <div
            style={{
              padding: "18px 20px",
              borderRadius: "22px",
              border: "1px dashed rgba(15, 95, 215, 0.35)",
              background: "rgba(255, 255, 255, 0.66)",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            Audit servisine su anda erisilemiyor. Backend hazır oldugunda bu ekran sistem
            kayıtlarını ritim, aksiyon ve varlık sinyalleriyle birlikte gerçek veriden gösterecek.
          </div>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "14px",
              }}
            >
              {metricCard("Toplam Kayıt", String(dashboard.summary.total_entries), "Denetim omurgasindaki tüm olaylar", "accent")}
              {metricCard("Son 7 Gün", String(dashboard.summary.last_7_days), "Yeni ritim ve taze hareketler")}
              {metricCard("Esiz Kullanıcı", String(dashboard.summary.unique_actors), "Kayıt izi birden fazla elde mi")}
              {metricCard("Esiz Varlık", String(dashboard.summary.unique_entities), "Hangi modüller daha cok oynuyor")}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                gap: "14px",
              }}
            >
              {decisionDeck.map((item) => (
                <div key={`${item.eyebrow}-${item.title}`}>{narrativeCard(item)}</div>
              ))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "16px",
              }}
            >
              {listCard(
                "Son Sistem Sinyalleri",
                "En yeni audit hareketlerini actor, aksiyon ve varlık bağlamıyla birlikte oku.",
                dashboard.recent_entries.map((entry) => ({
                  title: `${entry.action_type} · ${entry.entity_type} #${entry.entity_id}`,
                  meta: `${formatTimestamp(entry.created_at)} · ${formatActor(entry)}${entry.actor_role ? ` · ${entry.actor_role}` : ""} · ${entry.summary || "Özet bilgisi yok."}`,
                  value: entry.actor_username || "sistem",
                })),
              )}
              {listCard(
                "Aksiyon Dagilimi",
                "Son hareketler hangi aksiyon türünde yogunlasiyor bak.",
                actionMix.map(([action, count]) => ({
                  title: action,
                  meta: "Son audit hareketleri icindeki tekrar sayisi",
                  value: `${count} kayıt`,
                })),
              )}
              {listCard(
                "Varlık Baskisi",
                "Hangi modüller sistem kayıtlarını daha cok uretmis görünüyor.",
                entityMix.map(([entity, count]) => ({
                  title: entity,
                  meta: "Son audit kayıtları icindeki varlık yoğunluğu",
                  value: `${count} kayıt`,
                })),
              )}
            </div>

            <AuditManagementWorkspace />
          </>
        )}
      </section>
    </AppShell>
  );
}
