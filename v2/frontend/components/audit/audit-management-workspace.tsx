"use client";

import type { CSSProperties } from "react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";

import { apiFetch } from "../../lib/api";

type AuditEntry = {
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
};

type AuditManagementResponse = {
  total_entries: number;
  entries: AuditEntry[];
  action_options: string[];
  entity_options: string[];
  actor_options: string[];
};

const serifStyle = {
  fontFamily: '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
  letterSpacing: "-0.04em",
} as const;

const fieldStyle: CSSProperties = {
  width: "100%",
  padding: "13px 14px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.9)",
  color: "var(--text)",
  font: "inherit",
};

function badge(kind: "accent" | "soft" | "muted"): CSSProperties {
  const palette = {
    accent: {
      background: "rgba(15, 95, 215, 0.1)",
      color: "#0f5fd7",
      border: "1px solid rgba(15, 95, 215, 0.14)",
    },
    soft: {
      background: "rgba(16, 185, 129, 0.12)",
      color: "#0f9f6e",
      border: "1px solid rgba(16, 185, 129, 0.16)",
    },
    muted: {
      background: "rgba(95, 118, 152, 0.1)",
      color: "#5f7698",
      border: "1px solid rgba(95, 118, 152, 0.12)",
    },
  }[kind];
  return {
    display: "inline-flex",
    alignItems: "center",
    padding: "6px 10px",
    borderRadius: "999px",
    fontSize: "0.76rem",
    fontWeight: 800,
    ...palette,
  };
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

function truncateText(value: string, limit = 120) {
  if (!value) {
    return "-";
  }
  return value.length > limit ? `${value.slice(0, limit)}...` : value;
}

function actorLabel(entry: AuditEntry | null) {
  if (!entry) {
    return "-";
  }
  return entry.actor_full_name || entry.actor_username || "-";
}

function countValues(values: string[]) {
  const counts = new Map<string, number>();
  values.forEach((value) => {
    counts.set(value, (counts.get(value) ?? 0) + 1);
  });
  return [...counts.entries()].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "tr"));
}

function statCard(label: string, value: string, note: string, tone: "accent" | "soft" = "soft") {
  return (
    <article
      style={{
        padding: "16px 16px 14px",
        borderRadius: "18px",
        border: "1px solid var(--line)",
        background:
          tone === "accent"
            ? "linear-gradient(180deg, rgba(255,253,247,0.98), rgba(246,239,228,0.96))"
            : "rgba(255,255,255,0.86)",
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
        {label}
      </div>
      <div
        style={{
          ...serifStyle,
          fontSize: "1.4rem",
          lineHeight: 0.96,
          fontWeight: 700,
        }}
      >
        {value}
      </div>
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.9rem",
          lineHeight: 1.55,
        }}
      >
        {note}
      </div>
    </article>
  );
}

export function AuditManagementWorkspace() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [actionOptions, setActionOptions] = useState<string[]>([]);
  const [entityOptions, setEntityOptions] = useState<string[]>([]);
  const [actorOptions, setActorOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const deferredSearch = useDeferredValue(searchInput);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [actorFilter, setActorFilter] = useState("");

  async function loadEntries() {
    setLoading(true);
    setError("");
    try {
      const query = new URLSearchParams();
      query.set("limit", "240");
      if (actionFilter) {
        query.set("action_type", actionFilter);
      }
      if (entityFilter) {
        query.set("entity_type", entityFilter);
      }
      if (actorFilter) {
        query.set("actor_name", actorFilter);
      }
      if (deferredSearch.trim()) {
        query.set("search", deferredSearch.trim());
      }

      const response = await apiFetch(`/audit/records?${query.toString()}`);
      if (!response.ok) {
        throw new Error("Sistem kayıtları yüklenemedi.");
      }
      const payload = (await response.json()) as AuditManagementResponse;
      setEntries(payload.entries);
      setTotalEntries(payload.total_entries);
      setActionOptions(payload.action_options);
      setEntityOptions(payload.entity_options);
      setActorOptions(payload.actor_options);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Sistem kayıtları yüklenemedi.");
      setEntries([]);
      setTotalEntries(0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadEntries();
  }, [deferredSearch, actionFilter, entityFilter, actorFilter]);

  const topEntry = useMemo(() => entries[0] ?? null, [entries]);
  const activeFilterCount = useMemo(
    () => [deferredSearch.trim(), actionFilter, entityFilter, actorFilter].filter(Boolean).length,
    [deferredSearch, actionFilter, entityFilter, actorFilter],
  );
  const dominantAction = useMemo(() => countValues(entries.map((entry) => entry.action_type))[0] ?? null, [entries]);
  const dominantEntity = useMemo(() => countValues(entries.map((entry) => entry.entity_type))[0] ?? null, [entries]);

  function clearFilters() {
    setSearchInput("");
    setActionFilter("");
    setEntityFilter("");
    setActorFilter("");
  }

  return (
    <section
      style={{
        display: "grid",
        gap: "18px",
        padding: "22px",
        borderRadius: "26px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
        boxShadow: "0 18px 42px rgba(20, 39, 67, 0.06)",
      }}
    >
      <div
        style={{
          display: "grid",
          gap: "14px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "14px",
            alignItems: "start",
            flexWrap: "wrap",
          }}
        >
          <div style={{ display: "grid", gap: "8px", maxWidth: "68ch" }}>
            <div
              style={{
                display: "inline-flex",
                width: "fit-content",
                padding: "7px 11px",
                borderRadius: "999px",
                background: "rgba(15,95,215,0.08)",
                color: "#0f5fd7",
                fontSize: "0.75rem",
                fontWeight: 800,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              Kayıt Akışı
            </div>
            <h2
              style={{
                ...serifStyle,
                margin: 0,
                fontSize: "clamp(1.8rem, 3vw, 2.5rem)",
                lineHeight: 0.98,
                fontWeight: 700,
              }}
            >
              Sistem izini kullanıcı, modül ve aksiyon bazında takip ediyoruz.
            </h2>
            <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.75 }}>
              Filtreleri kullanarak hangi aksiyonun, hangi kayıtta ve hangi kullanıcı tarafından
              yapıldığını hızlıca kontrol edin.
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gap: "10px",
              minWidth: "260px",
            }}
          >
            <article
              style={{
                padding: "16px 18px",
                borderRadius: "22px",
                background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(35,54,78,0.94))",
                color: "#fff7ea",
                boxShadow: "var(--shadow-deep)",
                display: "grid",
                gap: "10px",
              }}
            >
              <div
                style={{
                  color: "rgba(255,247,234,0.62)",
                  fontSize: "0.74rem",
                  fontWeight: 800,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                }}
              >
                Audit Özeti
              </div>
              <div
                style={{
                  ...serifStyle,
                  fontSize: "1.7rem",
                  lineHeight: 0.95,
                  fontWeight: 700,
                }}
              >
                {loading ? "akim okunuyor" : `${entries.length} görünen kayıt`}
              </div>
              <div
                style={{
                  color: "rgba(255,247,234,0.72)",
                  lineHeight: 1.65,
                  fontSize: "0.92rem",
                }}
              >
                {loading
                  ? "Filtrelenmis audit kayıtları hazırlanıyor."
                  : `${totalEntries} toplam kayıt içinde bu görünum su anki audit penceresini temsil ediyor.`}
              </div>
            </article>

            {activeFilterCount > 0 ? (
              <button
                type="button"
                onClick={clearFilters}
                style={{
                  padding: "12px 14px",
                  borderRadius: "16px",
                  border: "1px solid rgba(15,95,215,0.16)",
                  background: "rgba(15,95,215,0.08)",
                  color: "#0f5fd7",
                  fontWeight: 800,
                  cursor: "pointer",
                }}
              >
                Filtreleri Temizle
              </button>
            ) : null}
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
            gap: "12px",
          }}
        >
          {statCard("Gorunen Kayıt", loading ? "..." : String(entries.length), "Bu filtrede masaya dusen satir sayisi", "accent")}
          {statCard(
            "Aktif Filtre",
            String(activeFilterCount),
            activeFilterCount ? "Audit akışinin kapsamı daraltılmış durumda" : "Tüm akış geniş açıda görünüyor",
          )}
          {statCard(
            "Baskin Aksiyon",
            dominantAction ? dominantAction[0] : "-",
            dominantAction ? `${dominantAction[1]} kayıtla tekrar ediyor` : "Aksiyon ritmi geldikçe burada belirir",
          )}
          {statCard(
            "Baskin Varlık",
            dominantEntity ? dominantEntity[0] : "-",
            dominantEntity ? `${dominantEntity[1]} kayıtla öne çıkıyor` : "Varlık yoğunluğu geldikçe burada belirir",
          )}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(320px, 1.25fr) minmax(290px, 0.85fr)",
          gap: "18px",
          alignItems: "start",
        }}
      >
        <div style={{ display: "grid", gap: "16px" }}>
          <div
            style={{
              padding: "18px",
              borderRadius: "22px",
              border: "1px solid var(--line)",
              background: "rgba(255,255,255,0.82)",
              display: "grid",
              gap: "12px",
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(220px, 1.4fr) repeat(3, minmax(160px, 1fr))",
                gap: "12px",
              }}
            >
              <input
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Özet, detay, varlık veya kullanıcı ara"
                style={fieldStyle}
              />
              <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)} style={fieldStyle}>
                <option value="">Tüm Aksiyonlar</option>
                {actionOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
              <select value={entityFilter} onChange={(event) => setEntityFilter(event.target.value)} style={fieldStyle}>
                <option value="">Tüm Varliklar</option>
                {entityOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
              <select value={actorFilter} onChange={(event) => setActorFilter(event.target.value)} style={fieldStyle}>
                <option value="">Tüm Kullanicilar</option>
                {actorOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </div>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
              }}
            >
              <span style={badge("muted")}>{totalEntries} toplam kayıt</span>
              {deferredSearch.trim() ? <span style={badge("accent")}>Arama aktif</span> : null}
              {actionFilter ? <span style={badge("soft")}>Aksiyon: {actionFilter}</span> : null}
              {entityFilter ? <span style={badge("soft")}>Varlık: {entityFilter}</span> : null}
              {actorFilter ? <span style={badge("soft")}>Kullanıcı: {actorFilter}</span> : null}
            </div>
          </div>

          <div
            style={{
              borderRadius: "22px",
              border: "1px solid var(--line)",
              overflow: "hidden",
              background: "rgba(255, 255, 255, 0.86)",
              boxShadow: "0 18px 42px rgba(20, 39, 67, 0.05)",
            }}
          >
            <div
              style={{
                padding: "14px 16px",
                borderBottom: "1px solid var(--line)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "grid", gap: "4px" }}>
                <strong>Sistem Kayıtları</strong>
                <span style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                  Kim, neyi, ne zaman değiştirdi sorusunun filtrelenmis görünümü
                </span>
              </div>
              <span style={badge("muted")}>{entries.length} satir</span>
            </div>

            <div style={{ maxHeight: "660px", overflow: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Zaman", "Kullanıcı", "Aksiyon", "Varlık", "Özet", "Detay"].map((label) => (
                      <th
                        key={label}
                        style={{
                          textAlign: "left",
                          padding: "14px 16px",
                          fontSize: "0.8rem",
                          color: "var(--muted)",
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                          fontWeight: 800,
                          borderBottom: "1px solid var(--line)",
                          background: "rgba(245, 248, 255, 0.92)",
                          position: "sticky",
                          top: 0,
                          zIndex: 1,
                        }}
                      >
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan={6} style={{ padding: "18px 16px", color: "var(--muted)" }}>
                        Sistem kayıtları yükleniyor...
                      </td>
                    </tr>
                  ) : error ? (
                    <tr>
                      <td colSpan={6} style={{ padding: "18px 16px", color: "#c24141" }}>
                        {error}
                      </td>
                    </tr>
                  ) : !entries.length ? (
                    <tr>
                      <td colSpan={6} style={{ padding: "18px 16px", color: "var(--muted)" }}>
                        Bu filtrelerde kayıt bulunamadı.
                      </td>
                    </tr>
                  ) : (
                    entries.map((entry) => (
                      <tr key={entry.id}>
                        <td
                          style={{
                            padding: "14px 16px",
                            borderBottom: "1px solid rgba(219, 228, 243, 0.7)",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {formatTimestamp(entry.created_at)}
                        </td>
                        <td
                          style={{
                            padding: "14px 16px",
                            borderBottom: "1px solid rgba(219, 228, 243, 0.7)",
                          }}
                        >
                          <div style={{ fontWeight: 700 }}>{entry.actor_full_name || "-"}</div>
                          <div style={{ color: "var(--muted)", fontSize: "0.86rem", marginTop: "4px" }}>
                            {entry.actor_role || "-"} • {entry.actor_username || "-"}
                          </div>
                        </td>
                        <td
                          style={{
                            padding: "14px 16px",
                            borderBottom: "1px solid rgba(219, 228, 243, 0.7)",
                            whiteSpace: "nowrap",
                          }}
                        >
                          <span style={badge("accent")}>{entry.action_type || "-"}</span>
                        </td>
                        <td
                          style={{
                            padding: "14px 16px",
                            borderBottom: "1px solid rgba(219, 228, 243, 0.7)",
                          }}
                        >
                          <div style={{ fontWeight: 700 }}>{entry.entity_type || "-"}</div>
                          <div style={{ color: "var(--muted)", fontSize: "0.86rem", marginTop: "4px" }}>
                            ID: {entry.entity_id || "-"}
                          </div>
                        </td>
                        <td
                          style={{
                            padding: "14px 16px",
                            borderBottom: "1px solid rgba(219, 228, 243, 0.7)",
                            minWidth: "260px",
                          }}
                        >
                          {truncateText(entry.summary, 140)}
                        </td>
                        <td
                          style={{
                            padding: "14px 16px",
                            borderBottom: "1px solid rgba(219, 228, 243, 0.7)",
                            minWidth: "280px",
                            color: "var(--muted)",
                          }}
                        >
                          {truncateText(entry.details_json, 160)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <aside
          style={{
            display: "grid",
            gap: "14px",
          }}
        >
          <article
            style={{
              padding: "18px",
              borderRadius: "22px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.9)",
              boxShadow: "0 18px 42px rgba(20, 39, 67, 0.05)",
              display: "grid",
              gap: "12px",
            }}
          >
            <div
              style={{
                color: "var(--muted)",
                fontSize: "0.74rem",
                textTransform: "uppercase",
                fontWeight: 800,
                letterSpacing: "0.08em",
              }}
            >
              Son Kayıt Özeti
            </div>
            <h3
              style={{
                ...serifStyle,
                margin: 0,
                fontSize: "1.45rem",
                lineHeight: 0.98,
              }}
            >
              {topEntry?.summary || "Henüz kayıt yok"}
            </h3>
            <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
              {topEntry
                ? `${actorLabel(topEntry)} • ${topEntry.entity_type || "-"} • ${formatTimestamp(topEntry.created_at)}`
                : "Kayıt akışı geldiğinde son islem burada daha editoryal bir özetle görünür."}
            </p>
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "8px",
              }}
            >
              <span style={badge("soft")}>{topEntry?.action_type || "Aksiyon bekleniyor"}</span>
              {topEntry?.entity_type ? <span style={badge("muted")}>{topEntry.entity_type}</span> : null}
            </div>
            <div
              style={{
                padding: "14px",
                borderRadius: "16px",
                border: "1px solid var(--line)",
                background: "rgba(245, 248, 255, 0.7)",
                color: "var(--muted)",
                lineHeight: 1.6,
                fontSize: "0.92rem",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {topEntry?.details_json
                ? truncateText(topEntry.details_json, 360)
                : "Detay JSON kaydı geldiğinde burada kisa onizleme gosterilir."}
            </div>
          </article>

          <article
            style={{
              padding: "18px",
              borderRadius: "22px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.9)",
              boxShadow: "0 18px 42px rgba(20, 39, 67, 0.05)",
              display: "grid",
              gap: "12px",
            }}
          >
            <div
              style={{
                color: "var(--muted)",
                fontSize: "0.74rem",
                textTransform: "uppercase",
                fontWeight: 800,
                letterSpacing: "0.08em",
              }}
            >
              Hızlı Okuma
            </div>
            <div
              style={{
                display: "grid",
                gap: "10px",
              }}
            >
              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: "16px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.78)",
                }}
              >
                <div style={{ color: "var(--muted)", fontSize: "0.76rem", fontWeight: 800, textTransform: "uppercase" }}>
                  Son Oyuncu
                </div>
                <div style={{ marginTop: "8px", fontWeight: 800 }}>{actorLabel(topEntry)}</div>
              </div>
              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: "16px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.78)",
                }}
              >
                <div style={{ color: "var(--muted)", fontSize: "0.76rem", fontWeight: 800, textTransform: "uppercase" }}>
                  Tekrarlayan Aksiyon
                </div>
                <div style={{ marginTop: "8px", fontWeight: 800 }}>
                  {dominantAction ? `${dominantAction[0]} · ${dominantAction[1]} kayıt` : "-"}
                </div>
              </div>
              <div
                style={{
                  padding: "12px 14px",
                  borderRadius: "16px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.78)",
                }}
              >
                <div style={{ color: "var(--muted)", fontSize: "0.76rem", fontWeight: 800, textTransform: "uppercase" }}>
                  Baskı Noktasi
                </div>
                <div style={{ marginTop: "8px", fontWeight: 800 }}>
                  {dominantEntity ? `${dominantEntity[0]} · ${dominantEntity[1]} kayıt` : "-"}
                </div>
              </div>
            </div>
          </article>
        </aside>
      </div>
    </section>
  );
}
