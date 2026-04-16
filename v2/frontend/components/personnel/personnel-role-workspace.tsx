"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import { apiFetch } from "../../lib/api";

type PersonnelRoleSummary = {
  total_history_records: number;
  active_personnel: number;
  distinct_roles: number;
  fixed_cost_cards: number;
};

type PersonnelRolePerson = {
  id: number;
  person_code: string;
  full_name: string;
  role: string;
  status: string;
  restaurant_label: string;
  cost_model: string;
  monthly_fixed_cost: number;
  role_history_count: number;
};

type PersonnelRoleHistory = {
  id: number;
  personnel_id: number;
  person_code: string;
  full_name: string;
  status: string;
  restaurant_label: string;
  role: string;
  cost_model: string;
  monthly_fixed_cost: number;
  effective_date: string | null;
  notes: string;
};

type PersonnelRoleWorkspaceResponse = {
  summary: PersonnelRoleSummary;
  people: PersonnelRolePerson[];
  history: PersonnelRoleHistory[];
};

type PersonnelFormOptions = {
  role_options: string[];
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

const costModelLabels: Record<string, string> = {
  fixed_kurye: "Sabit Kurye",
  fixed_bolge_muduru: "Sabit Bölge Müdürü",
  fixed_saha_denetmen_sefi: "Sabit Saha Denetmen Şefi",
  fixed_restoran_takim_sefi: "Sabit Restoran Takım Şefi",
  fixed_joker: "Sabit Joker",
};

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

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function pill(label: string, tone: "accent" | "soft" | "ink") {
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
      <div style={{ fontSize: "1.7rem", lineHeight: 0.92, fontWeight: 800 }}>{value}</div>
      <div style={{ color: "var(--muted)", lineHeight: 1.6, fontSize: "0.9rem" }}>{note}</div>
    </article>
  );
}

export function PersonnelRoleWorkspace() {
  const router = useRouter();
  const { user } = useAuth();
  const [isPending, startTransition] = useTransition();
  const [workspace, setWorkspace] = useState<PersonnelRoleWorkspaceResponse | null>(null);
  const [roleOptions, setRoleOptions] = useState<string[]>(["Kurye"]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null);
  const [role, setRole] = useState("Kurye");
  const [monthlyFixedCost, setMonthlyFixedCost] = useState("0");
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");

  async function loadWorkspace() {
    setLoading(true);
    setError("");
    try {
      const [workspaceResponse, optionsResponse] = await Promise.all([
        apiFetch("/personnel/role-workspace?limit=120"),
        apiFetch("/personnel/form-options"),
      ]);
      if (!workspaceResponse.ok) {
        throw new Error("Rol çalışma alanı yüklenemedi.");
      }
      const workspacePayload = (await workspaceResponse.json()) as PersonnelRoleWorkspaceResponse;
      setWorkspace(workspacePayload);
      setSelectedPersonId((current) => {
        if (!workspacePayload.people.length) {
          return null;
        }
        if (current && workspacePayload.people.some((person) => person.id === current)) {
          return current;
        }
        return workspacePayload.people[0].id;
      });
      if (optionsResponse.ok) {
        const optionsPayload = (await optionsResponse.json()) as PersonnelFormOptions;
        if (optionsPayload.role_options.length) {
          setRoleOptions(optionsPayload.role_options);
          setRole((current) => (optionsPayload.role_options.includes(current) ? current : optionsPayload.role_options[0]));
        }
      }
    } catch (nextError) {
      setWorkspace(null);
      setSelectedPersonId(null);
      setError(nextError instanceof Error ? nextError.message : "Rol çalışma alanı yüklenemedi.");
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

  const selectedHistory = useMemo(
    () => workspace?.history.filter((entry) => entry.personnel_id === selectedPersonId).slice(0, 6) ?? [],
    [selectedPersonId, workspace],
  );

  useEffect(() => {
    if (!selectedPerson) {
      return;
    }
    setRole(selectedPerson.role);
    setMonthlyFixedCost(String(selectedPerson.monthly_fixed_cost ?? 0));
  }, [selectedPerson]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPersonId) {
      setError("Önce bir personel seç.");
      return;
    }
    setError("");
    setSuccess("");

    const response = await apiFetch("/personnel/role-history", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personnel_id: selectedPersonId,
        role,
        monthly_fixed_cost: Number(monthlyFixedCost || 0),
        effective_date: effectiveDate || null,
        notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setError(payload?.detail || "Rol geçmişi güncellenemedi.");
      return;
    }

    setSuccess(payload?.message || "Rol geçmişi güncellendi.");
    setNotes("");
    await loadWorkspace();
    startTransition(() => {
      router.refresh();
    });
  }

  if (!(user?.allowed_actions.includes("personnel.list") && user.allowed_actions.includes("personnel.update"))) {
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Rol Geçişleri</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Personelin rol değişimini, başlangıç tarihini ve sabit maliyet çizgisini ayrı bir geçmiş
          masasında takip ediyoruz.
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
          Rol geçmişi yükleniyor...
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
          {error || "Rol çalışma alanı şu anda açılamıyor."}
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
            {metricCard("Geçmiş Kayıt", String(workspace.summary.total_history_records), "Toplam rol geçişi satırı")}
            {metricCard("Aktif Personel", String(workspace.summary.active_personnel), "Aktif kadro içinde yaşayan kartlar")}
            {metricCard("Rol Çeşidi", String(workspace.summary.distinct_roles), "Geçmişte görülen farklı rol başlıkları")}
            {metricCard("Sabit Kart", String(workspace.summary.fixed_cost_cards), "Sabit maliyetli aktif kartlar")}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(320px, 0.95fr) minmax(0, 1.05fr)",
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
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "10px", alignItems: "center" }}>
                      <strong>{person.full_name}</strong>
                      {pill(person.person_code, "accent")}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                      {pill(person.role, "soft")}
                      {pill(person.status, person.status === "Aktif" ? "ink" : "soft")}
                    </div>
                    <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>{person.restaurant_label}</div>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "10px", alignItems: "center" }}>
                      <div style={{ fontWeight: 700 }}>
                        {costModelLabels[person.cost_model] || person.cost_model || "Maliyet modeli yok"}
                      </div>
                      <span style={{ color: "var(--muted)", fontSize: "0.86rem", fontWeight: 700 }}>
                        {person.role_history_count} kayıt
                      </span>
                    </div>
                    <div style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                      {formatCurrency(person.monthly_fixed_cost)}
                    </div>
                  </button>
                ))
              ) : (
                <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>Henüz rol geçmişi görünmüyor.</div>
              )}
            </aside>

            <div style={{ display: "grid", gap: "16px" }}>
              {selectedPerson ? (
                <>
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
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center", flexWrap: "wrap" }}>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: "1.05rem" }}>{selectedPerson.full_name}</div>
                        <div style={{ color: "var(--muted)", marginTop: "4px" }}>
                          {selectedPerson.role} • {selectedPerson.restaurant_label}
                        </div>
                      </div>
                      {pill(costModelLabels[selectedPerson.cost_model] || selectedPerson.cost_model, "soft")}
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px" }}>
                      <div>
                        <div style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 700 }}>Güncel Rol</div>
                        <div style={{ marginTop: "6px", fontWeight: 800 }}>{selectedPerson.role}</div>
                      </div>
                      <div>
                        <div style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 700 }}>Sabit Maliyet</div>
                        <div style={{ marginTop: "6px", fontWeight: 800 }}>{formatCurrency(selectedPerson.monthly_fixed_cost)}</div>
                      </div>
                      <div>
                        <div style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: 700 }}>Geçmiş Sayısı</div>
                        <div style={{ marginTop: "6px", fontWeight: 800 }}>{selectedPerson.role_history_count}</div>
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
                        <span style={{ fontWeight: 700 }}>Yeni rol</span>
                        <select value={role} onChange={(event) => setRole(event.target.value)} style={fieldStyle}>
                          {roleOptions.map((item) => (
                            <option key={item} value={item}>
                              {item}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label style={{ display: "grid", gap: "8px" }}>
                        <span style={{ fontWeight: 700 }}>Başlangıç tarihi</span>
                        <input type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} style={fieldStyle} />
                      </label>
                      <label style={{ display: "grid", gap: "8px" }}>
                        <span style={{ fontWeight: 700 }}>Aylık sabit maliyet</span>
                        <input value={monthlyFixedCost} onChange={(event) => setMonthlyFixedCost(event.target.value)} style={fieldStyle} />
                      </label>
                      <label style={{ display: "grid", gap: "8px" }}>
                        <span style={{ fontWeight: 700 }}>Not</span>
                        <input value={notes} onChange={(event) => setNotes(event.target.value)} style={fieldStyle} />
                      </label>
                    </div>
                    {error ? (
                      <div style={{ padding: "12px 14px", borderRadius: "14px", background: "rgba(208, 67, 35, 0.08)", color: "#b6482b" }}>
                        {error}
                      </div>
                    ) : null}
                    {success ? (
                      <div style={{ padding: "12px 14px", borderRadius: "14px", background: "rgba(34, 139, 93, 0.1)", color: "#1d7d53" }}>
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
                      Rol Geçişini Kaydet
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
                      <div style={{ fontWeight: 800, fontSize: "1.02rem" }}>Seçili personelin son rol hareketleri</div>
                      <div style={{ color: "var(--muted)", marginTop: "4px", lineHeight: 1.65 }}>
                        Rol değişimi ve maliyet geçişi bu masada ayrı bir iz olarak tutulur.
                      </div>
                    </div>
                    {selectedHistory.length ? (
                      <div style={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                          <thead>
                            <tr style={{ textAlign: "left", background: "rgba(239,232,219,0.56)" }}>
                              {["Başlangıç", "Rol", "Maliyet Modeli", "Sabit Maliyet", "Not"].map((header) => (
                                <th key={header} style={{ padding: "12px 14px", fontSize: "0.76rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--muted)" }}>
                                  {header}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {selectedHistory.map((item) => (
                              <tr key={item.id} style={{ borderTop: "1px solid rgba(62,81,107,0.08)" }}>
                                <td style={{ padding: "12px 14px" }}>{formatDate(item.effective_date)}</td>
                                <td style={{ padding: "12px 14px", fontWeight: 700 }}>{item.role}</td>
                                <td style={{ padding: "12px 14px" }}>{costModelLabels[item.cost_model] || item.cost_model || "-"}</td>
                                <td style={{ padding: "12px 14px" }}>{formatCurrency(item.monthly_fixed_cost)}</td>
                                <td style={{ padding: "12px 14px" }}>{item.notes || "-"}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div style={{ color: "var(--muted)", lineHeight: 1.7 }}>
                        Seçili personel için henüz rol geçmişi görünmüyor.
                      </div>
                    )}
                  </article>
                </>
              ) : (
                <div
                  style={{
                    padding: "18px",
                    borderRadius: "18px",
                    border: "1px dashed var(--line)",
                    color: "var(--muted)",
                  }}
                >
                  Rol hattını başlatmak için soldan bir personel seç.
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
