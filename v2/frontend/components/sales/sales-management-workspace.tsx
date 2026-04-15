"use client";

import type { CSSProperties, FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type SalesEntry = {
  id: number;
  restaurant_name: string;
  city: string;
  district: string;
  address: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  requested_courier_count: number;
  lead_source: string;
  proposed_quote: number;
  pricing_model: string;
  pricing_model_label: string;
  pricing_model_hint: string;
  hourly_rate: number;
  package_rate: number;
  package_threshold: number;
  package_rate_low: number;
  package_rate_high: number;
  fixed_monthly_fee: number;
  status: string;
  next_follow_up_date: string | null;
  assigned_owner: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

type SalesManagementResponse = {
  total_entries: number;
  entries: SalesEntry[];
};

type SalesDetailResponse = {
  entry: SalesEntry;
};

type SalesFormOptions = {
  pricing_models: Array<{ value: string; label: string }>;
  source_options: string[];
  status_options: string[];
  selected_pricing_model: string;
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

function formatCurrency(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function pill(kind: "accent" | "muted"): CSSProperties {
  const palette = {
    accent: {
      background: "rgba(15, 95, 215, 0.1)",
      color: "#0f5fd7",
      border: "1px solid rgba(15, 95, 215, 0.14)",
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

export function SalesManagementWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<SalesFormOptions | null>(null);
  const [entries, setEntries] = useState<SalesEntry[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const deferredSearch = useDeferredValue(searchInput);
  const [filterStatus, setFilterStatus] = useState("");
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

  const [editRestaurantName, setEditRestaurantName] = useState("");
  const [editCity, setEditCity] = useState("");
  const [editDistrict, setEditDistrict] = useState("");
  const [editAddress, setEditAddress] = useState("");
  const [editContactName, setEditContactName] = useState("");
  const [editContactPhone, setEditContactPhone] = useState("");
  const [editContactEmail, setEditContactEmail] = useState("");
  const [editRequestedCourierCount, setEditRequestedCourierCount] = useState("1");
  const [editLeadSource, setEditLeadSource] = useState("");
  const [editPricingModel, setEditPricingModel] = useState("hourly_plus_package");
  const [editHourlyRate, setEditHourlyRate] = useState("0");
  const [editPackageRate, setEditPackageRate] = useState("0");
  const [editPackageThreshold, setEditPackageThreshold] = useState("390");
  const [editPackageRateLow, setEditPackageRateLow] = useState("0");
  const [editPackageRateHigh, setEditPackageRateHigh] = useState("0");
  const [editFixedMonthlyFee, setEditFixedMonthlyFee] = useState("0");
  const [editProposedQuote, setEditProposedQuote] = useState("0");
  const [editStatus, setEditStatus] = useState("");
  const [editNextFollowUpDate, setEditNextFollowUpDate] = useState("");
  const [editAssignedOwner, setEditAssignedOwner] = useState("");
  const [editNotes, setEditNotes] = useState("");

  async function loadOptions() {
    const response = await apiFetch("/sales/form-options");
    if (!response.ok) {
      throw new Error("Satış referans verileri yuklenemedi.");
    }
    const payload = (await response.json()) as SalesFormOptions;
    setOptions(payload);
  }

  async function loadEntries() {
    setListLoading(true);
    setListError("");
    try {
      const query = new URLSearchParams();
      query.set("limit", "160");
      if (filterStatus) {
        query.set("status", filterStatus);
      }
      if (deferredSearch.trim()) {
        query.set("search", deferredSearch.trim());
      }
      const response = await apiFetch(`/sales/records?${query.toString()}`);
      if (!response.ok) {
        throw new Error("Satış listesi yuklenemedi.");
      }
      const payload = (await response.json()) as SalesManagementResponse;
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
    } catch (error) {
      setListError(error instanceof Error ? error.message : "Satış listesi yuklenemedi.");
      setEntries([]);
      setTotalEntries(0);
      setSelectedEntryId(null);
    } finally {
      setListLoading(false);
    }
  }

  async function loadEntryDetail(entryId: number) {
    setDetailLoading(true);
    setSaveError("");
    setSaveSuccess("");
    try {
      const response = await apiFetch(`/sales/records/${entryId}`);
      if (!response.ok) {
        throw new Error("Satış detayi yuklenemedi.");
      }
      const payload = (await response.json()) as SalesDetailResponse;
      const entry = payload.entry;
      setEditRestaurantName(entry.restaurant_name);
      setEditCity(entry.city);
      setEditDistrict(entry.district);
      setEditAddress(entry.address ?? "");
      setEditContactName(entry.contact_name);
      setEditContactPhone(entry.contact_phone);
      setEditContactEmail(entry.contact_email ?? "");
      setEditRequestedCourierCount(String(entry.requested_courier_count ?? 0));
      setEditLeadSource(entry.lead_source || options?.source_options[0] || "");
      setEditPricingModel(entry.pricing_model || "hourly_plus_package");
      setEditHourlyRate(String(entry.hourly_rate ?? 0));
      setEditPackageRate(String(entry.package_rate ?? 0));
      setEditPackageThreshold(String(entry.package_threshold ?? 390));
      setEditPackageRateLow(String(entry.package_rate_low ?? 0));
      setEditPackageRateHigh(String(entry.package_rate_high ?? 0));
      setEditFixedMonthlyFee(String(entry.fixed_monthly_fee ?? 0));
      setEditProposedQuote(String(entry.proposed_quote ?? 0));
      setEditStatus(entry.status || options?.status_options[0] || "");
      setEditNextFollowUpDate(entry.next_follow_up_date ?? "");
      setEditAssignedOwner(entry.assigned_owner ?? "");
      setEditNotes(entry.notes ?? "");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Satış detayi yuklenemedi.");
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
  }, [options, deferredSearch, filterStatus]);

  useEffect(() => {
    if (selectedEntryId == null) {
      return;
    }
    void loadEntryDetail(selectedEntryId);
  }, [selectedEntryId, options]);

  const selectedEntry = useMemo(
    () => entries.find((entry) => entry.id === selectedEntryId) ?? null,
    [entries, selectedEntryId],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEntryId) {
      setSaveError("Duzenlenecek satış kaydı seç.");
      return;
    }

    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/sales/records/${selectedEntryId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_name: editRestaurantName,
        city: editCity,
        district: editDistrict,
        address: editAddress,
        contact_name: editContactName,
        contact_phone: editContactPhone,
        contact_email: editContactEmail,
        requested_courier_count: Number(editRequestedCourierCount || 0),
        lead_source: editLeadSource,
        proposed_quote: Number(editProposedQuote || 0),
        pricing_model: editPricingModel,
        hourly_rate: Number(editHourlyRate || 0),
        package_rate: Number(editPackageRate || 0),
        package_threshold: Number(editPackageThreshold || 390),
        package_rate_low: Number(editPackageRateLow || 0),
        package_rate_high: Number(editPackageRateHigh || 0),
        fixed_monthly_fee: Number(editFixedMonthlyFee || 0),
        status: editStatus,
        next_follow_up_date: editNextFollowUpDate || null,
        assigned_owner: editAssignedOwner,
        notes: editNotes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSaveError(payload?.detail || "Satış kaydı güncellenemedi.");
      return;
    }

    setSaveSuccess(payload?.message || "Satış kaydı güncellendi.");
    startTransition(() => {
      router.refresh();
    });
    await loadEntries();
    await loadEntryDetail(selectedEntryId);
  }

  async function handleDelete() {
    if (!selectedEntryId) {
      setSaveError("Silinecek satış kaydini seç.");
      return;
    }
    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/sales/records/${selectedEntryId}`, { method: "DELETE" });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSaveError(payload?.detail || "Satış kaydı silinemedi.");
      return;
    }
    setSaveSuccess(payload?.message || "Satış kaydı silindi.");
    startTransition(() => {
      router.refresh();
    });
    await loadEntries();
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Satış Kayıt Yonetimi</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Firsatlari filtrele, seç, güncelle ve tek panelden takip et.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(320px, 1.05fr) minmax(320px, 0.95fr)",
          gap: "16px",
          alignItems: "start",
        }}
      >
        <div style={{ display: "grid", gap: "14px" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(160px, 0.8fr) minmax(220px, 1.4fr)",
              gap: "12px",
            }}
          >
            <select value={filterStatus} onChange={(event) => setFilterStatus(event.target.value)} style={fieldStyle}>
              <option value="">Tüm Durumlar</option>
              {options?.status_options.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Restoran, ilce, yetkili veya sorumlu ara"
              style={fieldStyle}
            />
          </div>

          <div
            style={{
              padding: "14px 16px",
              borderRadius: "18px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.86)",
              color: "var(--muted)",
              fontWeight: 700,
            }}
          >
            Toplam eslesen fırsat: {totalEntries}
          </div>

          {listError ? (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "16px",
                border: "1px solid rgba(205, 70, 66, 0.18)",
                background: "rgba(205, 70, 66, 0.08)",
                color: "#b53632",
                fontWeight: 700,
              }}
            >
              {listError}
            </div>
          ) : (
            <div
              style={{
                display: "grid",
                gap: "10px",
                maxHeight: "620px",
                overflow: "auto",
                paddingRight: "4px",
              }}
            >
              {listLoading ? (
                <div
                  style={{
                    padding: "18px",
                    borderRadius: "18px",
                    border: "1px solid var(--line)",
                    background: "rgba(255, 255, 255, 0.72)",
                    color: "var(--muted)",
                  }}
                >
                  Satış kayıtları yükleniyor...
                </div>
              ) : entries.length === 0 ? (
                <div
                  style={{
                    padding: "18px",
                    borderRadius: "18px",
                    border: "1px dashed rgba(15, 95, 215, 0.25)",
                    background: "rgba(255, 255, 255, 0.72)",
                    color: "var(--muted)",
                  }}
                >
                  Bu filtrelerle eslesen satış kaydı bulunamadı.
                </div>
              ) : (
                entries.map((entry) => {
                  const isActive = entry.id === selectedEntryId;
                  return (
                    <button
                      key={entry.id}
                      type="button"
                      onClick={() => setSelectedEntryId(entry.id)}
                      style={{
                        textAlign: "left",
                        borderRadius: "20px",
                        border: isActive ? "1px solid rgba(15, 95, 215, 0.28)" : "1px solid var(--line)",
                        background: isActive ? "rgba(15, 95, 215, 0.08)" : "rgba(255, 255, 255, 0.88)",
                        padding: "16px",
                        display: "grid",
                        gap: "10px",
                        cursor: "pointer",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "start" }}>
                        <div>
                          <div style={{ fontWeight: 800 }}>{entry.restaurant_name}</div>
                          <div style={{ color: "var(--muted)", fontSize: "0.92rem", marginTop: "4px" }}>
                            {entry.city} / {entry.district}
                          </div>
                        </div>
                        <span style={pill(isActive ? "accent" : "muted")}>{entry.status}</span>
                      </div>
                      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                        <span style={pill("muted")}>{entry.pricing_model_label}</span>
                        <span style={pill("muted")}>{entry.lead_source || "Kaynak yok"}</span>
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "10px" }}>
                        <div>
                          <div style={{ fontSize: "0.78rem", color: "var(--muted)" }}>Yetkili</div>
                          <div style={{ fontWeight: 700 }}>{entry.contact_name || "-"}</div>
                        </div>
                        <div>
                          <div style={{ fontSize: "0.78rem", color: "var(--muted)" }}>Teklif</div>
                          <div style={{ fontWeight: 700 }}>{formatCurrency(entry.proposed_quote)}</div>
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
          <div
            style={{
              padding: "18px",
              borderRadius: "20px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.82)",
              display: "grid",
              gap: "10px",
            }}
          >
            <div style={{ fontSize: "0.82rem", letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--accent)", fontWeight: 800 }}>
              Seçili Fırsat
            </div>
            {selectedEntry ? (
              <>
                <div style={{ fontWeight: 800, fontSize: "1.05rem" }}>{selectedEntry.restaurant_name}</div>
                <div style={{ color: "var(--muted)" }}>
                  {selectedEntry.city} / {selectedEntry.district} • {selectedEntry.contact_name}
                </div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <span style={pill("accent")}>{selectedEntry.status}</span>
                  <span style={pill("muted")}>{selectedEntry.pricing_model_label}</span>
                </div>
              </>
            ) : (
              <div style={{ color: "var(--muted)" }}>Düzenlemek için soldan bir kayıt seç.</div>
            )}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "12px",
            }}
          >
            <input value={editRestaurantName} onChange={(event) => setEditRestaurantName(event.target.value)} placeholder="Restoran Adi" style={fieldStyle} />
            <input value={editCity} onChange={(event) => setEditCity(event.target.value)} placeholder="Il" style={fieldStyle} />
            <input value={editDistrict} onChange={(event) => setEditDistrict(event.target.value)} placeholder="Ilce" style={fieldStyle} />
            <input value={editRequestedCourierCount} onChange={(event) => setEditRequestedCourierCount(event.target.value)} placeholder="Kurye Sayisi" style={fieldStyle} />
            <input value={editContactName} onChange={(event) => setEditContactName(event.target.value)} placeholder="Yetkili" style={fieldStyle} />
            <input value={editContactPhone} onChange={(event) => setEditContactPhone(event.target.value)} placeholder="Telefon" style={fieldStyle} />
            <input value={editContactEmail} onChange={(event) => setEditContactEmail(event.target.value)} placeholder="Mail" style={fieldStyle} />
            <input value={editAssignedOwner} onChange={(event) => setEditAssignedOwner(event.target.value)} placeholder="Ilgilenen Kisi" style={fieldStyle} />
            <select value={editLeadSource} onChange={(event) => setEditLeadSource(event.target.value)} style={fieldStyle}>
              {options?.source_options.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
            <select value={editStatus} onChange={(event) => setEditStatus(event.target.value)} style={fieldStyle}>
              {options?.status_options.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
            <select value={editPricingModel} onChange={(event) => setEditPricingModel(event.target.value)} style={fieldStyle}>
              {options?.pricing_models.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
            <input type="date" value={editNextFollowUpDate} onChange={(event) => setEditNextFollowUpDate(event.target.value)} style={fieldStyle} />
          </div>

          <textarea value={editAddress} onChange={(event) => setEditAddress(event.target.value)} rows={2} placeholder="Adres" style={{ ...fieldStyle, resize: "vertical" }} />

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "12px",
            }}
          >
            {(editPricingModel === "hourly_plus_package" || editPricingModel === "hourly_only" || editPricingModel === "threshold_package") && (
              <input value={editHourlyRate} onChange={(event) => setEditHourlyRate(event.target.value)} placeholder="Saatlik Ucret" style={fieldStyle} />
            )}
            {editPricingModel === "hourly_plus_package" && (
              <input value={editPackageRate} onChange={(event) => setEditPackageRate(event.target.value)} placeholder="Paket Ucreti" style={fieldStyle} />
            )}
            {editPricingModel === "threshold_package" && (
              <>
                <input value={editPackageThreshold} onChange={(event) => setEditPackageThreshold(event.target.value)} placeholder="Esik" style={fieldStyle} />
                <input value={editPackageRateLow} onChange={(event) => setEditPackageRateLow(event.target.value)} placeholder="Esik Alti" style={fieldStyle} />
                <input value={editPackageRateHigh} onChange={(event) => setEditPackageRateHigh(event.target.value)} placeholder="Esik Ustu" style={fieldStyle} />
              </>
            )}
            {editPricingModel === "fixed_monthly" && (
              <input value={editFixedMonthlyFee} onChange={(event) => setEditFixedMonthlyFee(event.target.value)} placeholder="Aylık Tutar" style={fieldStyle} />
            )}
            <input value={editProposedQuote} onChange={(event) => setEditProposedQuote(event.target.value)} placeholder="Onerilen Teklif" style={fieldStyle} />
          </div>

          <textarea value={editNotes} onChange={(event) => setEditNotes(event.target.value)} rows={3} placeholder="Notlar" style={{ ...fieldStyle, resize: "vertical" }} />

          <div
            style={{
              padding: "14px 16px",
              borderRadius: "18px",
              border: "1px solid var(--line)",
              background: "rgba(255, 255, 255, 0.82)",
              color: "var(--muted)",
              lineHeight: 1.7,
            }}
          >
            <div style={{ fontWeight: 800, color: "var(--text)", marginBottom: "4px" }}>Teklif Özet Notu</div>
            {selectedEntry?.pricing_model_hint || "Seçili teklif modelinin açılımı burada görünür."}
          </div>

          {(saveError || saveSuccess) && (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "16px",
                border: saveError ? "1px solid rgba(205, 70, 66, 0.18)" : "1px solid rgba(35, 148, 94, 0.18)",
                background: saveError ? "rgba(205, 70, 66, 0.08)" : "rgba(35, 148, 94, 0.08)",
                color: saveError ? "#b53632" : "#1d7b4d",
                fontWeight: 700,
              }}
            >
              {saveError || saveSuccess}
            </div>
          )}

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <button
              type="submit"
              disabled={isPending || detailLoading}
              style={{
                appearance: "none",
                border: "none",
                borderRadius: "18px",
                padding: "14px 18px",
                background: "linear-gradient(135deg, #0f5fd7, #2563eb)",
                color: "white",
                fontWeight: 800,
                cursor: isPending ? "wait" : "pointer",
                boxShadow: "0 18px 40px rgba(15, 95, 215, 0.22)",
              }}
            >
              {isPending ? "Kaydediliyor..." : "Güncelle"}
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={isPending || detailLoading || !selectedEntryId}
              style={{
                appearance: "none",
                border: "1px solid rgba(205, 70, 66, 0.2)",
                borderRadius: "18px",
                padding: "14px 18px",
                background: "rgba(205, 70, 66, 0.08)",
                color: "#b53632",
                fontWeight: 800,
                cursor: isPending ? "wait" : "pointer",
              }}
            >
              Sil
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
