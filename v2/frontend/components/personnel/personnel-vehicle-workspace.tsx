"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "../../components/auth/auth-provider";
import { apiFetch } from "../../lib/api";

type PersonnelVehicleSummary = {
  total_history_records: number;
  active_catkapinda_vehicle_personnel: number;
  rental_cards: number;
  sale_cards: number;
};

type PersonnelVehiclePerson = {
  id: number;
  person_code: string;
  full_name: string;
  role: string;
  status: string;
  restaurant_label: string;
  vehicle_mode: string;
  current_plate: string;
  motor_rental_monthly_amount: number;
  motor_purchase_start_date: string | null;
  motor_purchase_commitment_months: number;
  motor_purchase_sale_price: number;
  motor_purchase_monthly_deduction: number;
  vehicle_history_count: number;
};

type PersonnelVehicleHistory = {
  id: number;
  personnel_id: number;
  person_code: string;
  full_name: string;
  role: string;
  status: string;
  restaurant_label: string;
  vehicle_mode: string;
  current_plate: string;
  motor_rental_monthly_amount: number;
  motor_purchase_start_date: string | null;
  motor_purchase_commitment_months: number;
  motor_purchase_sale_price: number;
  motor_purchase_monthly_deduction: number;
  effective_date: string | null;
  notes: string;
};

type PersonnelVehicleWorkspaceResponse = {
  summary: PersonnelVehicleSummary;
  people: PersonnelVehiclePerson[];
  history: PersonnelVehicleHistory[];
};

const vehicleModeOptions = [
  "Kendi Motoru",
  "Çat Kapında Motor Kirası",
  "Çat Kapında Motor Satışı",
];

const fieldStyle: CSSProperties = {
  width: "100%",
  padding: "13px 14px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.92)",
  color: "var(--text)",
  font: "inherit",
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

export function PersonnelVehicleWorkspace() {
  const router = useRouter();
  const { user } = useAuth();
  const [isPending, startTransition] = useTransition();
  const [workspace, setWorkspace] = useState<PersonnelVehicleWorkspaceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [selectedPersonId, setSelectedPersonId] = useState<number | null>(null);
  const [vehicleMode, setVehicleMode] = useState(vehicleModeOptions[0]);
  const [rentalAmount, setRentalAmount] = useState("13000");
  const [purchaseStartDate, setPurchaseStartDate] = useState("");
  const [purchaseCommitmentMonths, setPurchaseCommitmentMonths] = useState("0");
  const [purchaseSalePrice, setPurchaseSalePrice] = useState("0");
  const [purchaseMonthlyDeduction, setPurchaseMonthlyDeduction] = useState("0");
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");

  async function loadWorkspace() {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch("/personnel/vehicle-workspace?limit=120");
      if (!response.ok) {
        throw new Error("Motor çalışma alanı yüklenemedi.");
      }
      const payload = (await response.json()) as PersonnelVehicleWorkspaceResponse;
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
      setError(nextError instanceof Error ? nextError.message : "Motor çalışma alanı yüklenemedi.");
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
    setVehicleMode(selectedPerson.vehicle_mode || "Kendi Motoru");
    setRentalAmount(String(selectedPerson.motor_rental_monthly_amount ?? 0));
    setPurchaseStartDate(selectedPerson.motor_purchase_start_date ?? "");
    setPurchaseCommitmentMonths(String(selectedPerson.motor_purchase_commitment_months ?? 0));
    setPurchaseSalePrice(String(selectedPerson.motor_purchase_sale_price ?? 0));
    setPurchaseMonthlyDeduction(String(selectedPerson.motor_purchase_monthly_deduction ?? 0));
  }, [selectedPerson]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPersonId) {
      setError("Önce bir personel seç.");
      return;
    }

    setError("");
    setSuccess("");
    const response = await apiFetch("/personnel/vehicle-history", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personnel_id: selectedPersonId,
        vehicle_mode: vehicleMode,
        motor_rental_monthly_amount: Number(rentalAmount || 0),
        motor_purchase_start_date: purchaseStartDate || null,
        motor_purchase_commitment_months: Number(purchaseCommitmentMonths || 0),
        motor_purchase_sale_price: Number(purchaseSalePrice || 0),
        motor_purchase_monthly_deduction: Number(purchaseMonthlyDeduction || 0),
        effective_date: effectiveDate || null,
        notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setError(payload?.detail || "Motor geçmişi güncellenemedi.");
      return;
    }

    setSuccess(payload?.message || "Motor geçmişi güncellendi.");
    setNotes("");
    await loadWorkspace();
    startTransition(() => {
      router.refresh();
    });
  }

  if (!(user?.allowed_actions.includes("personnel.list") && user.allowed_actions.includes("personnel.update"))) {
    return null;
  }

  const isRental = vehicleMode === "Çat Kapında Motor Kirası";
  const isSale = vehicleMode === "Çat Kapında Motor Satışı";

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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Motor Hattı</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Çat Kapında motor kirası, motor satışı ve kendi motoru geçişlerini ayrı bir geçmiş
          masasında topluyoruz.
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
          Motor geçmişi yükleniyor...
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
          {error || "Motor çalışma alanı şu anda açılamıyor."}
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
              "Toplam Geçiş",
              String(workspace.summary.total_history_records),
              "Motor hattındaki tüm araç geçiş kayıtları",
            )}
            {metricCard(
              "Çat Kapında",
              String(workspace.summary.active_catkapinda_vehicle_personnel),
              "Şu an Çat Kapında aracıyla görünen aktif personel",
            )}
            {metricCard(
              "Kira Kartı",
              String(workspace.summary.rental_cards),
              "Aylık motor kira çizgisinde duran aktif kartlar",
            )}
            {metricCard(
              "Satış Kartı",
              String(workspace.summary.sale_cards),
              "Motor satış planı açık olan aktif kartlar",
            )}
          </div>

          {error ? (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "18px",
                border: "1px solid rgba(178, 51, 51, 0.16)",
                background: "rgba(178, 51, 51, 0.08)",
                color: "#9f2a2a",
              }}
            >
              {error}
            </div>
          ) : null}
          {success ? (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "18px",
                border: "1px solid rgba(54, 125, 61, 0.16)",
                background: "rgba(54, 125, 61, 0.08)",
                color: "#2d6a35",
              }}
            >
              {success}
            </div>
          ) : null}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(250px, 0.95fr) minmax(0, 1.05fr)",
              gap: "16px",
            }}
          >
            <aside
              style={{
                display: "grid",
                gap: "12px",
                padding: "16px",
                borderRadius: "20px",
                border: "1px solid var(--line)",
                background: "rgba(255,255,255,0.9)",
                alignContent: "start",
              }}
            >
              <div>
                <div style={{ fontWeight: 800 }}>Personel listesi</div>
                <div style={{ marginTop: "4px", color: "var(--muted)", lineHeight: 1.6 }}>
                  Motor düzeni değişecek kartı soldan seçiyoruz.
                </div>
              </div>
              <div style={{ display: "grid", gap: "10px", maxHeight: "520px", overflowY: "auto" }}>
                {workspace.people.map((person) => {
                  const selected = person.id === selectedPersonId;
                  return (
                    <button
                      key={person.id}
                      type="button"
                      onClick={() => setSelectedPersonId(person.id)}
                      style={{
                        textAlign: "left",
                        padding: "14px",
                        borderRadius: "18px",
                        border: selected ? "1px solid rgba(15, 95, 215, 0.25)" : "1px solid var(--line)",
                        background: selected ? "rgba(15, 95, 215, 0.08)" : "rgba(255,255,255,0.88)",
                        cursor: "pointer",
                        display: "grid",
                        gap: "8px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
                        <div>
                          <div style={{ fontWeight: 800 }}>{person.full_name}</div>
                          <div style={{ marginTop: "4px", color: "var(--muted)", fontSize: "0.88rem" }}>
                            {person.person_code} · {person.restaurant_label}
                          </div>
                        </div>
                        {pill(person.status, person.status === "Aktif" ? "accent" : "soft")}
                      </div>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                        {pill(person.role, "ink")}
                        {pill(person.vehicle_mode || "Kendi Motoru", "soft")}
                      </div>
                      <div style={{ color: "var(--muted)", fontSize: "0.88rem", lineHeight: 1.6 }}>
                        Plaka: {person.current_plate || "-"} · Geçiş: {person.vehicle_history_count}
                      </div>
                    </button>
                  );
                })}
              </div>
            </aside>

            <div style={{ display: "grid", gap: "16px" }}>
              <form
                onSubmit={(event) => {
                  void handleSubmit(event);
                }}
                style={{
                  display: "grid",
                  gap: "14px",
                  padding: "18px",
                  borderRadius: "22px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.92)",
                }}
              >
                <div style={{ display: "grid", gap: "6px" }}>
                  <div style={{ fontWeight: 800 }}>Motor geçiş formu</div>
                  <div style={{ color: "var(--muted)", lineHeight: 1.6 }}>
                    Kira ve satış hatlarını tarihli şekilde ayrı kayıt altına alıyoruz.
                  </div>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                    gap: "12px",
                  }}
                >
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span>Motor düzeni</span>
                    <select value={vehicleMode} onChange={(event) => setVehicleMode(event.target.value)} style={fieldStyle}>
                      {vehicleModeOptions.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span>Geçiş tarihi</span>
                    <input type="date" value={effectiveDate} onChange={(event) => setEffectiveDate(event.target.value)} style={fieldStyle} />
                  </label>
                </div>

                {isRental ? (
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span>Aylık motor kira tutarı</span>
                    <input type="number" min="0" step="100" value={rentalAmount} onChange={(event) => setRentalAmount(event.target.value)} style={fieldStyle} />
                  </label>
                ) : null}

                {isSale ? (
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                      gap: "12px",
                    }}
                  >
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span>Satış başlangıç tarihi</span>
                      <input type="date" value={purchaseStartDate} onChange={(event) => setPurchaseStartDate(event.target.value)} style={fieldStyle} />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span>Taahhüt ayı</span>
                      <input type="number" min="0" step="1" value={purchaseCommitmentMonths} onChange={(event) => setPurchaseCommitmentMonths(event.target.value)} style={fieldStyle} />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span>Motor satış bedeli</span>
                      <input type="number" min="0" step="100" value={purchaseSalePrice} onChange={(event) => setPurchaseSalePrice(event.target.value)} style={fieldStyle} />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span>Aylık satış kesintisi</span>
                      <input type="number" min="0" step="100" value={purchaseMonthlyDeduction} onChange={(event) => setPurchaseMonthlyDeduction(event.target.value)} style={fieldStyle} />
                    </label>
                  </div>
                ) : null}

                <label style={{ display: "grid", gap: "8px" }}>
                  <span>Not</span>
                  <textarea
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    rows={3}
                    style={{ ...fieldStyle, resize: "vertical" }}
                    placeholder="Örn. yeni kira planı, motor satış geçişi, geçici iade"
                  />
                </label>

                <button
                  type="submit"
                  disabled={isPending || !selectedPersonId}
                  style={{
                    border: "none",
                    borderRadius: "16px",
                    padding: "14px 18px",
                    background: "linear-gradient(135deg, #1f5eff, #2055c9)",
                    color: "white",
                    fontWeight: 800,
                    cursor: isPending ? "wait" : "pointer",
                  }}
                >
                  {isPending ? "Kaydediliyor..." : "Motor geçmişine işle"}
                </button>
              </form>

              <section
                style={{
                  padding: "18px",
                  borderRadius: "22px",
                  border: "1px solid var(--line)",
                  background: "rgba(255,255,255,0.92)",
                  display: "grid",
                  gap: "14px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                  <div>
                    <div style={{ fontWeight: 800 }}>Seçili kart</div>
                    <div style={{ marginTop: "4px", color: "var(--muted)", lineHeight: 1.6 }}>
                      {selectedPerson ? `${selectedPerson.full_name} · ${selectedPerson.person_code}` : "Personel seç"}
                    </div>
                  </div>
                  {selectedPerson ? pill(selectedPerson.vehicle_mode || "Kendi Motoru", "accent") : null}
                </div>

                {selectedPerson ? (
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                      gap: "12px",
                    }}
                  >
                    <div style={{ padding: "12px 14px", borderRadius: "16px", background: "rgba(244,247,252,0.9)" }}>
                      <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Güncel plaka</div>
                      <div style={{ marginTop: "6px", fontWeight: 800 }}>{selectedPerson.current_plate || "-"}</div>
                    </div>
                    <div style={{ padding: "12px 14px", borderRadius: "16px", background: "rgba(244,247,252,0.9)" }}>
                      <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Aylık kira</div>
                      <div style={{ marginTop: "6px", fontWeight: 800 }}>{formatCurrency(selectedPerson.motor_rental_monthly_amount)}</div>
                    </div>
                    <div style={{ padding: "12px 14px", borderRadius: "16px", background: "rgba(244,247,252,0.9)" }}>
                      <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Satış kesintisi</div>
                      <div style={{ marginTop: "6px", fontWeight: 800 }}>{formatCurrency(selectedPerson.motor_purchase_monthly_deduction)}</div>
                    </div>
                    <div style={{ padding: "12px 14px", borderRadius: "16px", background: "rgba(244,247,252,0.9)" }}>
                      <div style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Taahhüt ayı</div>
                      <div style={{ marginTop: "6px", fontWeight: 800 }}>{selectedPerson.motor_purchase_commitment_months || 0}</div>
                    </div>
                  </div>
                ) : null}

                <div style={{ display: "grid", gap: "10px" }}>
                  {selectedHistory.length ? (
                    selectedHistory.map((entry) => (
                      <article
                        key={entry.id}
                        style={{
                          padding: "14px 16px",
                          borderRadius: "18px",
                          border: "1px solid var(--line)",
                          background: "rgba(250,248,243,0.92)",
                          display: "grid",
                          gap: "8px",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", flexWrap: "wrap" }}>
                          <strong>{entry.vehicle_mode}</strong>
                          {pill(formatDate(entry.effective_date), "soft")}
                        </div>
                        <div style={{ color: "var(--muted)", lineHeight: 1.6 }}>
                          Kira: {formatCurrency(entry.motor_rental_monthly_amount)} · Satış: {formatCurrency(entry.motor_purchase_sale_price)} · Aylık kesinti: {formatCurrency(entry.motor_purchase_monthly_deduction)}
                        </div>
                        <div style={{ color: "var(--muted)", lineHeight: 1.6 }}>
                          Satış başlangıcı: {formatDate(entry.motor_purchase_start_date)} · Taahhüt: {entry.motor_purchase_commitment_months || 0} ay
                        </div>
                        {entry.notes ? <div style={{ color: "var(--muted)", lineHeight: 1.6 }}>{entry.notes}</div> : null}
                      </article>
                    ))
                  ) : (
                    <div
                      style={{
                        padding: "14px 16px",
                        borderRadius: "18px",
                        border: "1px dashed var(--line)",
                        color: "var(--muted)",
                      }}
                    >
                      Seçili personel için henüz motor geçmişi kaydı yok.
                    </div>
                  )}
                </div>
              </section>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
