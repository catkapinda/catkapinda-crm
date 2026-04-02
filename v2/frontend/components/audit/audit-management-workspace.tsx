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

  return (
    <section
      style={{
        display: "grid",
        gap: "16px",
        padding: "22px",
        borderRadius: "24px",
        border: "1px solid var(--line)",
        background: "var(--surface-strong)",
      }}
    >
      <div>
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Kayıt Akışı</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Kim, hangi kayıt üzerinde ne yaptı bilgisini filtreleyip hızlıca inceleyin.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(320px, 1.2fr) minmax(280px, 0.8fr)",
          gap: "16px",
          alignItems: "start",
        }}
      >
        <div style={{ display: "grid", gap: "14px" }}>
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
              <option value="">Tüm Varlıklar</option>
              {entityOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
            <select value={actorFilter} onChange={(event) => setActorFilter(event.target.value)} style={fieldStyle}>
              <option value="">Tüm Kullanıcılar</option>
              {actorOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>

          <div
            style={{
              borderRadius: "20px",
              border: "1px solid var(--line)",
              overflow: "hidden",
              background: "rgba(255, 255, 255, 0.86)",
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
              <strong>Sistem Kayıtları</strong>
              <span style={badge("muted")}>{totalEntries} kayıt</span>
            </div>

            <div style={{ maxHeight: "620px", overflow: "auto" }}>
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
                        <td style={{ padding: "14px 16px", borderBottom: "1px solid rgba(219, 228, 243, 0.7)", whiteSpace: "nowrap" }}>
                          {formatTimestamp(entry.created_at)}
                        </td>
                        <td style={{ padding: "14px 16px", borderBottom: "1px solid rgba(219, 228, 243, 0.7)" }}>
                          <div style={{ fontWeight: 700 }}>{entry.actor_full_name || "-"}</div>
                          <div style={{ color: "var(--muted)", fontSize: "0.86rem", marginTop: "4px" }}>
                            {entry.actor_role || "-"} • {entry.actor_username || "-"}
                          </div>
                        </td>
                        <td style={{ padding: "14px 16px", borderBottom: "1px solid rgba(219, 228, 243, 0.7)", whiteSpace: "nowrap" }}>
                          <span style={badge("accent")}>{entry.action_type || "-"}</span>
                        </td>
                        <td style={{ padding: "14px 16px", borderBottom: "1px solid rgba(219, 228, 243, 0.7)" }}>
                          <div style={{ fontWeight: 700 }}>{entry.entity_type || "-"}</div>
                          <div style={{ color: "var(--muted)", fontSize: "0.86rem", marginTop: "4px" }}>
                            ID: {entry.entity_id || "-"}
                          </div>
                        </td>
                        <td style={{ padding: "14px 16px", borderBottom: "1px solid rgba(219, 228, 243, 0.7)", minWidth: "260px" }}>
                          {truncateText(entry.summary, 140)}
                        </td>
                        <td style={{ padding: "14px 16px", borderBottom: "1px solid rgba(219, 228, 243, 0.7)", minWidth: "280px", color: "var(--muted)" }}>
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
            padding: "18px",
            borderRadius: "20px",
            border: "1px solid var(--line)",
            background: "rgba(255, 255, 255, 0.9)",
          }}
        >
          <div>
            <div style={{ color: "var(--muted)", fontSize: "0.82rem", textTransform: "uppercase", fontWeight: 800 }}>
              Son Kayıt Özeti
            </div>
            <h3 style={{ margin: "10px 0 6px", fontSize: "1.1rem" }}>
              {topEntry?.summary || "Henüz kayıt yok"}
            </h3>
            <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
              {topEntry
                ? `${topEntry.actor_full_name || "-"} • ${topEntry.entity_type || "-"} • ${formatTimestamp(topEntry.created_at)}`
                : "Kayıt akışı geldiğinde son işlem burada özetlenir."}
            </p>
          </div>

          <div
            style={{
              display: "grid",
              gap: "10px",
            }}
          >
            <div style={{ ...badge("soft"), justifyContent: "center" }}>
              {topEntry?.action_type || "Aksiyon bekleniyor"}
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
                : "Detay JSON kaydı geldiğinde burada kısa önizleme gösterilir."}
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
