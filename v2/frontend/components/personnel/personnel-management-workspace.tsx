"use client";

import type { CSSProperties, FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type PersonnelEntry = {
  id: number;
  person_code: string;
  full_name: string;
  role: string;
  status: string;
  phone: string;
  restaurant_id: number | null;
  restaurant_label: string;
  vehicle_mode: string;
  current_plate: string;
  start_date: string | null;
  monthly_fixed_cost: number;
  notes: string;
};

type PersonnelFormOptions = {
  restaurants: Array<{
    id: number;
    label: string;
  }>;
  role_options: string[];
  status_options: string[];
  vehicle_mode_options: string[];
  selected_restaurant_id: number | null;
};

type PersonnelManagementResponse = {
  total_entries: number;
  entries: PersonnelEntry[];
};

type PersonnelDetailResponse = {
  entry: PersonnelEntry;
};

function pill(kind: "accent" | "soft"): CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    padding: "6px 10px",
    borderRadius: "999px",
    fontSize: "0.76rem",
    fontWeight: 800,
    ...(kind === "accent"
      ? {
          background: "rgba(15, 95, 215, 0.1)",
          color: "#0f5fd7",
          border: "1px solid rgba(15, 95, 215, 0.14)",
        }
      : {
          background: "rgba(95, 118, 152, 0.1)",
          color: "#5f7698",
          border: "1px solid rgba(95, 118, 152, 0.12)",
        }),
  };
}

const fieldStyle: CSSProperties = {
  width: "100%",
  padding: "13px 14px",
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.9)",
  color: "var(--text)",
  font: "inherit",
};

export function PersonnelManagementWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const [options, setOptions] = useState<PersonnelFormOptions | null>(null);
  const [entries, setEntries] = useState<PersonnelEntry[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const deferredSearch = useDeferredValue(searchInput);
  const [filterRestaurantId, setFilterRestaurantId] = useState<number | "">("");
  const [filterRole, setFilterRole] = useState<string>("");
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

  const [editFullName, setEditFullName] = useState("");
  const [editRole, setEditRole] = useState("Kurye");
  const [editPhone, setEditPhone] = useState("");
  const [editRestaurantId, setEditRestaurantId] = useState<number | "">("");
  const [editStatus, setEditStatus] = useState("Aktif");
  const [editVehicleMode, setEditVehicleMode] = useState("Kendi Motoru");
  const [editCurrentPlate, setEditCurrentPlate] = useState("");
  const [editStartDate, setEditStartDate] = useState("");
  const [editMonthlyFixedCost, setEditMonthlyFixedCost] = useState("0");
  const [editNotes, setEditNotes] = useState("");
  const [editPersonCode, setEditPersonCode] = useState("");

  async function loadOptions() {
    const response = await apiFetch("/personnel/form-options");
    if (!response.ok) {
      throw new Error("Personel referans verileri yuklenemedi.");
    }
    const payload = (await response.json()) as PersonnelFormOptions;
    setOptions(payload);
    if (!filterRestaurantId && payload.selected_restaurant_id) {
      setFilterRestaurantId(payload.selected_restaurant_id);
    }
  }

  async function loadEntries() {
    setListLoading(true);
    setError("");
    try {
      const query = new URLSearchParams();
      query.set("limit", "160");
      if (typeof filterRestaurantId === "number") {
        query.set("restaurant_id", String(filterRestaurantId));
      }
      if (filterRole) {
        query.set("role", filterRole);
      }
      if (deferredSearch.trim()) {
        query.set("search", deferredSearch.trim());
      }
      const response = await apiFetch(`/personnel/records?${query.toString()}`);
      if (!response.ok) {
        throw new Error("Personel listesi yuklenemedi.");
      }
      const payload = (await response.json()) as PersonnelManagementResponse;
      setEntries(payload.entries);
      setTotalEntries(payload.total_entries);
      setSelectedEntryId((current) => {
        if (!payload.entries.length) {
          return null;
        }
        if (current && payload.entries.some((entry) => entry.id === current)) {
          return current;
        }
        return payload.entries[0].id;
      });
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Personel listesi yuklenemedi.");
      setEntries([]);
      setTotalEntries(0);
      setSelectedEntryId(null);
    } finally {
      setListLoading(false);
    }
  }

  async function loadEntryDetail(entryId: number) {
    setDetailLoading(true);
    setError("");
    setSuccess("");
    try {
      const response = await apiFetch(`/personnel/records/${entryId}`);
      if (!response.ok) {
        throw new Error("Personel detayi yuklenemedi.");
      }
      const payload = (await response.json()) as PersonnelDetailResponse;
      const entry = payload.entry;
      setEditFullName(entry.full_name);
      setEditRole(entry.role);
      setEditPhone(entry.phone ?? "");
      setEditRestaurantId(entry.restaurant_id ?? "");
      setEditStatus(entry.status);
      setEditVehicleMode(entry.vehicle_mode);
      setEditCurrentPlate(entry.current_plate ?? "");
      setEditStartDate(entry.start_date ?? "");
      setEditMonthlyFixedCost(String(entry.monthly_fixed_cost ?? 0));
      setEditNotes(entry.notes ?? "");
      setEditPersonCode(entry.person_code);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Personel detayi yuklenemedi.");
    } finally {
      setDetailLoading(false);
    }
  }

  useEffect(() => {
    void loadOptions();
  }, []);

  useEffect(() => {
    if (!options) {
      return;
    }
    void loadEntries();
  }, [options, deferredSearch, filterRestaurantId, filterRole]);

  useEffect(() => {
    if (selectedEntryId == null) {
      return;
    }
    void loadEntryDetail(selectedEntryId);
  }, [selectedEntryId]);

  const selectedEntry = useMemo(
    () => entries.find((entry) => entry.id === selectedEntryId) ?? null,
    [entries, selectedEntryId],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEntryId) {
      setError("Duzenlenecek personel sec.");
      return;
    }
    setError("");
    setSuccess("");

    const response = await apiFetch(`/personnel/records/${selectedEntryId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        full_name: editFullName,
        role: editRole,
        phone: editPhone,
        assigned_restaurant_id: typeof editRestaurantId === "number" ? editRestaurantId : null,
        status: editStatus,
        start_date: editStartDate || null,
        vehicle_mode: editVehicleMode,
        current_plate: editCurrentPlate,
        monthly_fixed_cost: Number(editMonthlyFixedCost || 0),
        notes: editNotes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string; person_code?: string }
      | null;
    if (!response.ok) {
      setError(payload?.detail || "Personel kaydi guncellenemedi.");
      return;
    }
    setSuccess(payload?.message || "Personel kaydi guncellendi.");
    if (payload?.person_code) {
      setEditPersonCode(payload.person_code);
    }
    await loadEntries();
    startTransition(() => {
      router.refresh();
    });
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Personel Yonetimi</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Kodu, subesi, rolu ve arac atamasiyla birlikte personel kayitlarini attendance v2
          kalibinda yonet.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(320px, 1fr) minmax(0, 1.4fr)",
          gap: "16px",
          alignItems: "start",
        }}
      >
        <aside
          style={{
            display: "grid",
            gap: "14px",
            padding: "16px",
            borderRadius: "20px",
            border: "1px solid var(--line)",
            background: "rgba(244, 248, 255, 0.85)",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
              gap: "10px",
            }}
          >
            <Metric label="Toplam" value={String(totalEntries)} />
            <Metric label="Aktif Liste" value={String(entries.length)} />
          </div>

          <div
            style={{
              display: "grid",
              gap: "10px",
            }}
          >
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Ad, kod, telefon ara"
              style={fieldStyle}
            />
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: "10px",
              }}
            >
              <select
                value={filterRestaurantId}
                onChange={(event) =>
                  setFilterRestaurantId(event.target.value ? Number(event.target.value) : "")
                }
                style={fieldStyle}
              >
                <option value="">Tum Subeler</option>
                {options?.restaurants.map((restaurant) => (
                  <option key={restaurant.id} value={restaurant.id}>
                    {restaurant.label}
                  </option>
                ))}
              </select>
              <select value={filterRole} onChange={(event) => setFilterRole(event.target.value)} style={fieldStyle}>
                <option value="">Tum Roller</option>
                {options?.role_options.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div
            style={{
              maxHeight: "560px",
              overflow: "auto",
              display: "grid",
              gap: "10px",
            }}
          >
            {listLoading ? (
              <InlineMessage tone="soft" message="Personel listesi yukleniyor..." />
            ) : entries.length ? (
              entries.map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => setSelectedEntryId(entry.id)}
                  style={{
                    display: "grid",
                    gap: "10px",
                    padding: "14px",
                    borderRadius: "18px",
                    border: selectedEntryId === entry.id ? "1px solid rgba(15, 95, 215, 0.28)" : "1px solid var(--line)",
                    background: selectedEntryId === entry.id ? "rgba(15, 95, 215, 0.08)" : "#fff",
                    textAlign: "left",
                    cursor: "pointer",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: "10px",
                    }}
                  >
                    <div style={{ fontWeight: 800 }}>{entry.full_name}</div>
                    <span style={pill("accent")}>{entry.person_code}</span>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "8px",
                    }}
                  >
                    <span style={pill("soft")}>{entry.role}</span>
                    <span style={pill("soft")}>{entry.status}</span>
                    <span style={pill("soft")}>{entry.vehicle_mode}</span>
                  </div>
                  <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>
                    {entry.restaurant_label}
                  </div>
                </button>
              ))
            ) : (
              <InlineMessage tone="soft" message="Filtrelere uygun personel bulunamadi." />
            )}
          </div>
        </aside>

        <div
          style={{
            display: "grid",
            gap: "14px",
          }}
        >
          {selectedEntry ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1.6fr) minmax(260px, 320px)",
                gap: "16px",
                alignItems: "start",
              }}
            >
              <form
                onSubmit={handleSubmit}
                style={{
                  display: "grid",
                  gap: "14px",
                }}
              >
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                    gap: "14px",
                  }}
                >
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Ad Soyad</span>
                    <input value={editFullName} onChange={(event) => setEditFullName(event.target.value)} style={fieldStyle} />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Rol</span>
                    <select value={editRole} onChange={(event) => setEditRole(event.target.value)} style={fieldStyle}>
                      {options?.role_options.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Telefon</span>
                    <input value={editPhone} onChange={(event) => setEditPhone(event.target.value)} style={fieldStyle} />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Durum</span>
                    <select value={editStatus} onChange={(event) => setEditStatus(event.target.value)} style={fieldStyle}>
                      {options?.status_options.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Restoran / Sube</span>
                    <select
                      value={editRestaurantId}
                      onChange={(event) =>
                        setEditRestaurantId(event.target.value ? Number(event.target.value) : "")
                      }
                      style={fieldStyle}
                    >
                      <option value="">Atanmadi</option>
                      {options?.restaurants.map((restaurant) => (
                        <option key={restaurant.id} value={restaurant.id}>
                          {restaurant.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Arac Modu</span>
                    <select
                      value={editVehicleMode}
                      onChange={(event) => setEditVehicleMode(event.target.value)}
                      style={fieldStyle}
                    >
                      {options?.vehicle_mode_options.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Plaka</span>
                    <input value={editCurrentPlate} onChange={(event) => setEditCurrentPlate(event.target.value)} style={fieldStyle} />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Ise Giris</span>
                    <input type="date" value={editStartDate} onChange={(event) => setEditStartDate(event.target.value)} style={fieldStyle} />
                  </label>
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Aylik Sabit Tutar</span>
                    <input
                      inputMode="decimal"
                      value={editMonthlyFixedCost}
                      onChange={(event) => setEditMonthlyFixedCost(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                </div>

                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Not</span>
                  <textarea
                    value={editNotes}
                    onChange={(event) => setEditNotes(event.target.value)}
                    rows={3}
                    style={{ ...fieldStyle, resize: "vertical", minHeight: "96px" }}
                  />
                </label>

                <button
                  type="submit"
                  disabled={isPending || detailLoading}
                  style={{
                    padding: "14px 18px",
                    borderRadius: "16px",
                    border: "none",
                    background: "var(--accent)",
                    color: "#fff",
                    fontWeight: 800,
                    fontSize: "0.96rem",
                    cursor: "pointer",
                  }}
                >
                  {isPending ? "Guncelleniyor..." : "Personel Kaydini Guncelle"}
                </button>
                {error ? <InlineMessage tone="error" message={error} /> : null}
                {success ? <InlineMessage tone="success" message={success} /> : null}
              </form>

              <aside
                style={{
                  display: "grid",
                  gap: "12px",
                  padding: "16px",
                  borderRadius: "20px",
                  border: "1px solid var(--line)",
                  background: "rgba(244, 248, 255, 0.9)",
                }}
              >
                <h3 style={{ margin: 0, fontSize: "1rem" }}>Mevcut Kart</h3>
                <SummaryItem label="Kod" value={editPersonCode} />
                <SummaryItem label="Rol" value={editRole} />
                <SummaryItem label="Sube" value={selectedEntry.restaurant_label} />
                <SummaryItem label="Arac" value={editVehicleMode} />
                <SummaryItem label="Durum" value={editStatus} />
              </aside>
            </div>
          ) : (
            <InlineMessage tone="soft" message="Duzenlemek icin soldan bir personel sec." />
          )}
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        padding: "12px 14px",
        borderRadius: "16px",
        border: "1px solid rgba(193, 209, 232, 0.9)",
        background: "#fff",
        display: "grid",
        gap: "4px",
      }}
    >
      <span
        style={{
          color: "var(--muted)",
          fontSize: "0.78rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 800,
        }}
      >
        {label}
      </span>
      <span style={{ fontWeight: 900, fontSize: "1.15rem" }}>{value}</span>
    </div>
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "grid",
        gap: "4px",
        padding: "12px 14px",
        borderRadius: "16px",
        border: "1px solid rgba(193, 209, 232, 0.9)",
        background: "#fff",
      }}
    >
      <span
        style={{
          color: "var(--muted)",
          fontSize: "0.78rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 800,
        }}
      >
        {label}
      </span>
      <span style={{ fontWeight: 800 }}>{value || "-"}</span>
    </div>
  );
}

function InlineMessage({ tone, message }: { tone: "error" | "success" | "soft"; message: string }) {
  const palette =
    tone === "error"
      ? {
          background: "rgba(222, 66, 66, 0.09)",
          border: "1px solid rgba(222, 66, 66, 0.18)",
          color: "#b53a3a",
        }
      : tone === "success"
        ? {
            background: "rgba(38, 167, 107, 0.1)",
            border: "1px solid rgba(38, 167, 107, 0.16)",
            color: "#167f51",
          }
        : {
            background: "rgba(15, 95, 215, 0.06)",
            border: "1px solid rgba(15, 95, 215, 0.12)",
            color: "var(--muted)",
          };
  return (
    <div
      style={{
        padding: "14px 16px",
        borderRadius: "16px",
        ...palette,
      }}
    >
      {message}
    </div>
  );
}
