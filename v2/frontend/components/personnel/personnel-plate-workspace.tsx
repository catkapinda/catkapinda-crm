"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import { apiFetch } from "../../lib/api";

type PersonnelPlateSummary = {
  total_history_records: number;
  active_plate_assignments: number;
  active_catkapinda_vehicle_personnel: number;
  active_missing_plate_personnel: number;
};

type PersonnelPlatePerson = {
  id: number;
  person_code: string;
  full_name: string;
  role: string;
  status: string;
  restaurant_label: string;
  vehicle_mode: string;
  current_plate: string;
  plate_history_count: number;
};

type PersonnelPlateHistory = {
  id: number;
  personnel_id: number;
  person_code: string;
  full_name: string;
  role: string;
  restaurant_label: string;
  vehicle_mode: string;
  current_plate: string;
  plate: string;
  start_date: string | null;
  end_date: string | null;
  reason: string;
  active: boolean;
};

type PersonnelPlateWorkspaceResponse = {
  summary: PersonnelPlateSummary;
  people: PersonnelPlatePerson[];
  history: PersonnelPlateHistory[];
};

const fieldStyle: CSSProperties = {
  width: "100%",
  padding: "13px 14px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.92)",
  color: "var(--text)",
  font: "inherit",
};

function metricCard(label: string, value: string, note: string) {
  return (
    <article
      key={label}
      style={{
        padding: "14px 16px",
        borderRadius: "18px",
        border: "1px solid var(--line)",
        background: "rgba(255,255,255,0.88)",
        display: "grid",
        gap: "6px",
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
          fontSize: "1.7rem",
          lineHeight: 0.92,
          fontWeight: 800,
          color: "var(--text)",
        }}
      >
        {value}
      </div>
      <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.9rem" }}>{note}</div>
    </article>
  );
}

function statusPill(label: string, tone: "soft" | "accent" | "ink") {
  const palette =
    tone === "accent"
      ? {
          background: "rgba(15, 95, 215, 0.1)",
          color: "#0f5fd7",
          border: "1px solid rgba(15, 95, 215, 0.14)",
        }
      : tone === "ink"
        ? {
            background: "rgba(27, 42, 63, 0.12)",
            color: "#1b2a3f",
            border: "1px solid rgba(27, 42, 63, 0.12)",
          }
        : {
            background: "rgba(95, 118, 152, 0.1)",
            color: "#5f7698",
            border: "1px solid rgba(95, 118, 152, 0.12)",
          };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "6px 10px",
        borderRadius: "999px",
        fontSize: "0.76rem",
        fontWeight: 800,
        ...palette,
      }}
    >
      {label}
    </span>
  );
}

function formatDate(value: string | null) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("tr-TR").format(date);
}

export function PersonnelPlateWorkspace() {
  const router = useRouter();
  const { user } = useAuth();
  const [isPending, startTransition] = useTransition();
  const [workspace, setWorkspace] = useState<PersonnelPlateWorkspaceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null);
  const [plate, setPlate] = useState("");
  const [reason, setReason] = useState("Yeni zimmet");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState("");

  async function loadWorkspace() {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch("/personnel/plate-workspace?limit=120");
      if (!response.ok) {
        throw new Error("Plaka çalışma alanı yüklenemedi.");
      }
      const payload = (await response.json()) as PersonnelPlateWorkspaceResponse;
      setWorkspace(payload);
      setSelectedPersonId((current) => {
        if (!payload.people.length) {
          return null;
        }
        if (current && payload.people.some((person) => person.id === current)) {
          return current;
        }
        return payload.people[0].id;
      });
    } catch (nextError) {
      setWorkspace(null);
      setSelectedPersonId(null);
      setError(nextError instanceof Error ? nextError.message : "Plaka çalışma alanı yüklenemedi.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadWorkspace();
  }, []);

  const selectedPerson = useMemo(
    () => workspace?.people.find((person) => person.id === selectedPersonId) ?? null,
    [selectedPersonId, workspace],
  );
  const hasSelectedPerson = Boolean(selectedPerson);

  const selectedHistory = useMemo(
    () =>
      workspace?.history.filter((entry) => entry.personnel_id === selectedPersonId).slice(0, 6) ?? [],
    [selectedPersonId, workspace],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPersonId) {
      setError("Önce bir personel seç.");
      return;
    }
    if (!plate.trim()) {
      setError("Yeni plaka zorunlu.");
      return;
    }

    setError("");
    setSuccess("");
    const response = await apiFetch("/personnel/plate-history", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personnel_id: selectedPersonId,
        plate,
        reason,
        start_date: startDate || null,
        end_date: endDate || null,
      }),
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setError(payload?.detail || "Plaka geçmişi güncellenemedi.");
      return;
    }

    setSuccess(payload?.message || "Plaka geçmişi güncellendi.");
    setPlate("");
    setEndDate("");
    await loadWorkspace();
    startTransition(() => {
      router.refresh();
    });
  }

  if (!user?.allowed_actions.includes("personnel.plate")) {
    return null;
  }

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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Plaka ve Motor Geçmişi</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Araç zimmeti, plaka değişimi ve saha motor hattını personel kartından ayrı bir çalışma
          alanında yönetiyoruz.
        </p>
      </div>

      {loading ? (
        <div
          style={{
            padding: "18px",
            borderRadius: "18px",
            background: "rgba(15, 95, 215, 0.06)",
            color: "var(--muted)",
          }}
        >
          Plaka geçmişi yükleniyor...
        </div>
      ) : !workspace ? (
        <div
          style={{
            padding: "18px",
            borderRadius: "18px",
            border: "1px dashed var(--line)",
            color: "var(--muted)",
          }}
        >
          {error || "Plaka çalışma alanı şu anda açılamıyor."}
        </div>
      ) : (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "12px",
            }}
          >
            {metricCard(
              "Geçmiş Kayıt",
              String(workspace.summary.total_history_records),
              "Toplam plaka hareketi kaydı",
            )}
            {metricCard(
              "Açık Atama",
              String(workspace.summary.active_plate_assignments),
              "Şu anda aktif görünen plaka zimmetleri",
            )}
            {metricCard(
              "Çat Kapında Motor",
              String(workspace.summary.active_catkapinda_vehicle_personnel),
              "Aktif araç hattında olan personel",
            )}
            {metricCard(
              "Plakasız Aktif",
              String(workspace.summary.active_missing_plate_personnel),
              "Aktif kart içinde plaka bekleyenler",
            )}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: hasSelectedPerson
                ? "minmax(320px, 0.95fr) minmax(0, 1.05fr)"
                : "minmax(0, 1fr)",
              gap: "16px",
              alignItems: "start",
            }}
          >
            <aside
              style={{
                display: "grid",
                gap: "12px",
                padding: "16px",
                borderRadius: "20px",
                border: "1px solid var(--line)",
                background: "rgba(244, 248, 255, 0.85)",
                maxHeight: "640px",
                overflow: "auto",
              }}
            >
              {workspace.people.length ? (
                workspace.people.map((person) => (
                  <button
                    key={person.id}
                    type="button"
                    onClick={() => setSelectedPersonId(person.id)}
                    style={{
                      display: "grid",
                      gap: "10px",
                      padding: "14px",
                      borderRadius: "18px",
                      border:
                        selectedPersonId === person.id
                          ? "1px solid rgba(15, 95, 215, 0.28)"
                          : "1px solid var(--line)",
                      background:
                        selectedPersonId === person.id ? "rgba(15, 95, 215, 0.08)" : "#fff",
                      textAlign: "left",
                      cursor: "pointer",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "10px",
                        alignItems: "center",
                      }}
                    >
                      <strong>{person.full_name}</strong>
                      {statusPill(person.person_code, "accent")}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                      {statusPill(person.role, "soft")}
                      {statusPill(person.status, person.status === "Aktif" ? "ink" : "soft")}
                    </div>
                    <div style={{ color: "var(--muted)", fontSize: "0.92rem", lineHeight: 1.6 }}>
                      {person.restaurant_label}
                    </div>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "minmax(0, 1fr) auto",
                        gap: "10px",
                        alignItems: "center",
                      }}
                    >
                      <div style={{ color: "var(--text)", fontWeight: 700 }}>
                        {person.current_plate || "Plaka bekleniyor"}
                      </div>
                      <span style={{ color: "var(--muted)", fontSize: "0.86rem", fontWeight: 700 }}>
                        {person.plate_history_count} kayıt
                      </span>
                    </div>
                    <div style={{ color: "var(--muted)", fontSize: "0.88rem" }}>{person.vehicle_mode}</div>
                  </button>
                ))
              ) : (
                <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                  Henüz plaka hattına alınmış personel görünmüyor.
                </div>
              )}
            </aside>

            {selectedPerson ? (
              <div style={{ display: "grid", gap: "16px" }}>
                  <article
                    style={{
                      padding: "18px",
                      borderRadius: "20px",
                      border: "1px solid var(--line)",
                      background: "rgba(255,255,255,0.9)",
                      display: "grid",
                      gap: "12px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: "12px",
                        alignItems: "center",
                        flexWrap: "wrap",
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 800, fontSize: "1.05rem" }}>{selectedPerson.full_name}</div>
                        <div style={{ color: "var(--muted)", marginTop: "4px" }}>
                          {selectedPerson.role} • {selectedPerson.restaurant_label}
                        </div>
                      </div>
                      {statusPill(selectedPerson.vehicle_mode, "soft")}
                    </div>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                        gap: "12px",
                      }}
                    >
                      <div>
                        <div style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 700 }}>
                          Güncel Plaka
                        </div>
                        <div style={{ marginTop: "6px", fontWeight: 800 }}>
                          {selectedPerson.current_plate || "Henüz tanımlı değil"}
                        </div>
                      </div>
                      <div>
                        <div style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 700 }}>
                          Geçmiş Sayısı
                        </div>
                        <div style={{ marginTop: "6px", fontWeight: 800 }}>
                          {selectedPerson.plate_history_count}
                        </div>
                      </div>
                      <div>
                        <div style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 700 }}>
                          Kod
                        </div>
                        <div style={{ marginTop: "6px", fontWeight: 800 }}>{selectedPerson.person_code}</div>
                      </div>
                    </div>
                  </article>

                  <form
                    onSubmit={handleSubmit}
                    style={{
                      display: "grid",
                      gap: "14px",
                      padding: "18px",
                      borderRadius: "20px",
                      border: "1px solid var(--line)",
                      background: "rgba(255,253,247,0.92)",
                    }}
                  >
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                        gap: "12px",
                      }}
                    >
                      <label style={{ display: "grid", gap: "8px" }}>
                        <span style={{ fontWeight: 700 }}>Yeni plaka</span>
                        <input value={plate} onChange={(event) => setPlate(event.target.value)} style={fieldStyle} />
                      </label>
                      <label style={{ display: "grid", gap: "8px" }}>
                        <span style={{ fontWeight: 700 }}>Sebep</span>
                        <select value={reason} onChange={(event) => setReason(event.target.value)} style={fieldStyle}>
                          {["Yeni zimmet", "Kaza", "Bakım", "Geçici değişim", "Diğer"].map((item) => (
                            <option key={item} value={item}>
                              {item}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label style={{ display: "grid", gap: "8px" }}>
                        <span style={{ fontWeight: 700 }}>Başlangıç</span>
                        <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} style={fieldStyle} />
                      </label>
                      <label style={{ display: "grid", gap: "8px" }}>
                        <span style={{ fontWeight: 700 }}>Bitiş</span>
                        <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} style={fieldStyle} />
                      </label>
                    </div>
                    {error ? (
                      <div
                        style={{
                          padding: "12px 14px",
                          borderRadius: "14px",
                          background: "rgba(208, 67, 35, 0.08)",
                          color: "#b6482b",
                        }}
                      >
                        {error}
                      </div>
                    ) : null}
                    {success ? (
                      <div
                        style={{
                          padding: "12px 14px",
                          borderRadius: "14px",
                          background: "rgba(34, 139, 93, 0.1)",
                          color: "#1d7d53",
                        }}
                      >
                        {success}
                      </div>
                    ) : null}
                    <button
                      type="submit"
                      disabled={isPending}
                      style={{
                        border: 0,
                        borderRadius: "16px",
                        padding: "14px 18px",
                        background: "linear-gradient(135deg, var(--accent-strong), #9c5d14)",
                        color: "#fff7ea",
                        fontWeight: 800,
                        cursor: "pointer",
                      }}
                    >
                      Plaka Geçmişine Ekle
                    </button>
                  </form>

                  <article
                    style={{
                      padding: "18px",
                      borderRadius: "20px",
                      border: "1px solid var(--line)",
                      background: "rgba(255,255,255,0.9)",
                      display: "grid",
                      gap: "12px",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 800, fontSize: "1.02rem" }}>Seçili personelin son plaka hareketleri</div>
                      <div style={{ color: "var(--muted)", marginTop: "4px", lineHeight: 1.65 }}>
                        Bu akış personel kartındaki güncel plaka alanını ayrı bir geçmiş tablosu ile güvenceye alır.
                      </div>
                    </div>
                    {selectedHistory.length ? (
                      <div style={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <thead>
                            <tr style={{ textAlign: "left", background: "rgba(239,232,219,0.56)" }}>
                              {["Başlangıç", "Bitiş", "Plaka", "Sebep", "Durum"].map((header) => (
                                <th
                                  key={header}
                                  style={{
                                    padding: "12px 14px",
                                    fontSize: "0.76rem",
                                    textTransform: "uppercase",
                                    letterSpacing: "0.08em",
                                    color: "var(--muted)",
                                  }}
                                >
                                  {header}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {selectedHistory.map((item) => (
                              <tr key={item.id} style={{ borderTop: "1px solid rgba(62,81,107,0.08)" }}>
                                <td style={{ padding: "12px 14px" }}>{formatDate(item.start_date)}</td>
                                <td style={{ padding: "12px 14px" }}>{formatDate(item.end_date)}</td>
                                <td style={{ padding: "12px 14px", fontWeight: 700 }}>{item.plate}</td>
                                <td style={{ padding: "12px 14px" }}>{item.reason || "-"}</td>
                                <td style={{ padding: "12px 14px" }}>
                                  {statusPill(item.active ? "Aktif" : "Kapandı", item.active ? "accent" : "soft")}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                        Seçili personel için henüz plaka geçmişi görünmüyor.
                      </div>
                    )}
                  </article>
              </div>
            ) : null}
          </div>

          <article
            style={{
              padding: "18px",
              borderRadius: "20px",
              border: "1px solid var(--line)",
              background: "rgba(255,255,255,0.9)",
              display: "grid",
              gap: "12px",
            }}
          >
            <div>
              <div style={{ fontWeight: 800, fontSize: "1.02rem" }}>Son plaka hareketleri</div>
              <div style={{ color: "var(--muted)", marginTop: "4px", lineHeight: 1.65 }}>
                Son kayıtlar operasyonun hangi kartta araç değişimi yaptığını tek bakışta gösterir.
              </div>
            </div>
            {workspace.history.length ? (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ textAlign: "left", background: "rgba(239,232,219,0.56)" }}>
                      {["Başlangıç", "Personel", "Şube", "Plaka", "Sebep", "Durum"].map((header) => (
                        <th
                          key={header}
                          style={{
                            padding: "12px 14px",
                            fontSize: "0.76rem",
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                            color: "var(--muted)",
                          }}
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {workspace.history.map((item) => (
                      <tr key={item.id} style={{ borderTop: "1px solid rgba(62,81,107,0.08)" }}>
                        <td style={{ padding: "12px 14px" }}>{formatDate(item.start_date)}</td>
                        <td style={{ padding: "12px 14px" }}>
                          <div style={{ fontWeight: 700 }}>{item.full_name}</div>
                          <div style={{ color: "var(--muted)", fontSize: "0.86rem" }}>{item.person_code}</div>
                        </td>
                        <td style={{ padding: "12px 14px" }}>{item.restaurant_label}</td>
                        <td style={{ padding: "12px 14px", fontWeight: 700 }}>{item.plate}</td>
                        <td style={{ padding: "12px 14px" }}>{item.reason || "-"}</td>
                        <td style={{ padding: "12px 14px" }}>
                          {statusPill(item.active ? "Aktif" : "Kapandı", item.active ? "accent" : "soft")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                Henüz plaka geçmişi kaydı oluşmadı.
              </div>
            )}
          </article>
        </>
      )}
    </section>
  );
}
