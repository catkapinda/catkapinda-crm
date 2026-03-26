"use client";

import type { CSSProperties, FormEvent } from "react";
import { useDeferredValue, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type RestaurantEntry = {
  id: number;
  brand: string;
  branch: string;
  pricing_model: string;
  pricing_model_label: string;
  hourly_rate: number;
  package_rate: number;
  package_threshold: number;
  package_rate_low: number;
  package_rate_high: number;
  fixed_monthly_fee: number;
  vat_rate: number;
  target_headcount: number;
  start_date: string | null;
  end_date: string | null;
  extra_headcount_request: number;
  extra_headcount_request_date: string | null;
  reduce_headcount_request: number;
  reduce_headcount_request_date: string | null;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  company_title: string;
  address: string;
  tax_office: string;
  tax_number: string;
  active: boolean;
  notes: string;
};

type RestaurantsManagementResponse = {
  total_entries: number;
  entries: RestaurantEntry[];
};

type RestaurantDetailResponse = {
  entry: RestaurantEntry;
};

type RestaurantsFormOptions = {
  pricing_models: Array<{ value: string; label: string }>;
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

export function RestaurantManagementWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<RestaurantsFormOptions | null>(null);
  const [entries, setEntries] = useState<RestaurantEntry[]>([]);
  const [totalEntries, setTotalEntries] = useState(0);
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const deferredSearch = useDeferredValue(searchInput);
  const [filterPricingModel, setFilterPricingModel] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | "active" | "passive">("all");
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);

  const [editBrand, setEditBrand] = useState("");
  const [editBranch, setEditBranch] = useState("");
  const [editPricingModel, setEditPricingModel] = useState("hourly_plus_package");
  const [editStatus, setEditStatus] = useState("Aktif");
  const [editHourlyRate, setEditHourlyRate] = useState("0");
  const [editPackageRate, setEditPackageRate] = useState("0");
  const [editPackageThreshold, setEditPackageThreshold] = useState("390");
  const [editPackageRateLow, setEditPackageRateLow] = useState("0");
  const [editPackageRateHigh, setEditPackageRateHigh] = useState("0");
  const [editFixedMonthlyFee, setEditFixedMonthlyFee] = useState("0");
  const [editVatRate, setEditVatRate] = useState("20");
  const [editTargetHeadcount, setEditTargetHeadcount] = useState("1");
  const [editStartDate, setEditStartDate] = useState("");
  const [editEndDate, setEditEndDate] = useState("");
  const [editExtraHeadcountRequest, setEditExtraHeadcountRequest] = useState("0");
  const [editExtraHeadcountRequestDate, setEditExtraHeadcountRequestDate] = useState("");
  const [editReduceHeadcountRequest, setEditReduceHeadcountRequest] = useState("0");
  const [editReduceHeadcountRequestDate, setEditReduceHeadcountRequestDate] = useState("");
  const [editContactName, setEditContactName] = useState("");
  const [editContactPhone, setEditContactPhone] = useState("");
  const [editContactEmail, setEditContactEmail] = useState("");
  const [editCompanyTitle, setEditCompanyTitle] = useState("");
  const [editAddress, setEditAddress] = useState("");
  const [editTaxOffice, setEditTaxOffice] = useState("");
  const [editTaxNumber, setEditTaxNumber] = useState("");
  const [editNotes, setEditNotes] = useState("");

  async function loadOptions() {
    const response = await apiFetch("/restaurants/form-options");
    if (!response.ok) {
      throw new Error("Restoran referans verileri yuklenemedi.");
    }
    const payload = (await response.json()) as RestaurantsFormOptions;
    setOptions(payload);
  }

  async function loadEntries() {
    setListLoading(true);
    setListError("");
    try {
      const query = new URLSearchParams();
      query.set("limit", "180");
      if (filterPricingModel) {
        query.set("pricing_model", filterPricingModel);
      }
      if (filterStatus !== "all") {
        query.set("active", filterStatus === "active" ? "true" : "false");
      }
      if (deferredSearch.trim()) {
        query.set("search", deferredSearch.trim());
      }
      const response = await apiFetch(`/restaurants/records?${query.toString()}`);
      if (!response.ok) {
        throw new Error("Restoran listesi yuklenemedi.");
      }
      const payload = (await response.json()) as RestaurantsManagementResponse;
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
      setListError(error instanceof Error ? error.message : "Restoran listesi yuklenemedi.");
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
      const response = await apiFetch(`/restaurants/records/${entryId}`);
      if (!response.ok) {
        throw new Error("Restoran detayi yuklenemedi.");
      }
      const payload = (await response.json()) as RestaurantDetailResponse;
      const entry = payload.entry;
      setEditBrand(entry.brand);
      setEditBranch(entry.branch);
      setEditPricingModel(entry.pricing_model);
      setEditStatus(entry.active ? "Aktif" : "Pasif");
      setEditHourlyRate(String(entry.hourly_rate ?? 0));
      setEditPackageRate(String(entry.package_rate ?? 0));
      setEditPackageThreshold(String(entry.package_threshold ?? 390));
      setEditPackageRateLow(String(entry.package_rate_low ?? 0));
      setEditPackageRateHigh(String(entry.package_rate_high ?? 0));
      setEditFixedMonthlyFee(String(entry.fixed_monthly_fee ?? 0));
      setEditVatRate(String(entry.vat_rate ?? 20));
      setEditTargetHeadcount(String(entry.target_headcount ?? 0));
      setEditStartDate(entry.start_date ?? "");
      setEditEndDate(entry.end_date ?? "");
      setEditExtraHeadcountRequest(String(entry.extra_headcount_request ?? 0));
      setEditExtraHeadcountRequestDate(entry.extra_headcount_request_date ?? "");
      setEditReduceHeadcountRequest(String(entry.reduce_headcount_request ?? 0));
      setEditReduceHeadcountRequestDate(entry.reduce_headcount_request_date ?? "");
      setEditContactName(entry.contact_name ?? "");
      setEditContactPhone(entry.contact_phone ?? "");
      setEditContactEmail(entry.contact_email ?? "");
      setEditCompanyTitle(entry.company_title ?? "");
      setEditAddress(entry.address ?? "");
      setEditTaxOffice(entry.tax_office ?? "");
      setEditTaxNumber(entry.tax_number ?? "");
      setEditNotes(entry.notes ?? "");
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Restoran detayi yuklenemedi.");
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
  }, [options, deferredSearch, filterPricingModel, filterStatus]);

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

  const selectedPricingLabel = useMemo(
    () => options?.pricing_models.find((item) => item.value === editPricingModel)?.label ?? editPricingModel,
    [options, editPricingModel],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedEntryId) {
      setSaveError("Duzenlenecek restoran sec.");
      return;
    }

    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/restaurants/records/${selectedEntryId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        brand: editBrand,
        branch: editBranch,
        pricing_model: editPricingModel,
        hourly_rate: Number(editHourlyRate || 0),
        package_rate: Number(editPackageRate || 0),
        package_threshold: Number(editPackageThreshold || 390),
        package_rate_low: Number(editPackageRateLow || 0),
        package_rate_high: Number(editPackageRateHigh || 0),
        fixed_monthly_fee: Number(editFixedMonthlyFee || 0),
        vat_rate: Number(editVatRate || 20),
        target_headcount: Number(editTargetHeadcount || 0),
        start_date: editStartDate || null,
        end_date: editEndDate || null,
        extra_headcount_request: Number(editExtraHeadcountRequest || 0),
        extra_headcount_request_date: editExtraHeadcountRequestDate || null,
        reduce_headcount_request: Number(editReduceHeadcountRequest || 0),
        reduce_headcount_request_date: editReduceHeadcountRequestDate || null,
        contact_name: editContactName,
        contact_phone: editContactPhone,
        contact_email: editContactEmail,
        company_title: editCompanyTitle,
        address: editAddress,
        tax_office: editTaxOffice,
        tax_number: editTaxNumber,
        status: editStatus,
        notes: editNotes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSaveError(payload?.detail || "Restoran kaydi guncellenemedi.");
      return;
    }

    setSaveSuccess(payload?.message || "Restoran kaydi guncellendi.");
    startTransition(() => {
      router.refresh();
    });
    await loadEntries();
    await loadEntryDetail(selectedEntryId);
  }

  async function handleToggleStatus() {
    if (!selectedEntryId) {
      setSaveError("Durumu degistirilecek restoran sec.");
      return;
    }
    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/restaurants/records/${selectedEntryId}/toggle-status`, {
      method: "POST",
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSaveError(payload?.detail || "Restoran durumu degistirilemedi.");
      return;
    }
    setSaveSuccess(payload?.message || "Restoran durumu guncellendi.");
    startTransition(() => {
      router.refresh();
    });
    await loadEntries();
    await loadEntryDetail(selectedEntryId);
  }

  async function handleDelete() {
    if (!selectedEntryId) {
      setSaveError("Silinecek restoran sec.");
      return;
    }
    setSaveError("");
    setSaveSuccess("");

    const response = await apiFetch(`/restaurants/records/${selectedEntryId}`, {
      method: "DELETE",
    });
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSaveError(payload?.detail || "Restoran kaydi silinemedi.");
      return;
    }
    setSaveSuccess(payload?.message || "Restoran kaydi silindi.");
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Restoran Kayit Yonetimi</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Sube kartlarini filtrele, sec, guncelle, pasife al veya kalici olarak sil.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(320px, 1.05fr) minmax(280px, 0.95fr)",
          gap: "16px",
          alignItems: "start",
        }}
      >
        <div
          style={{
            display: "grid",
            gap: "14px",
            padding: "18px",
            borderRadius: "20px",
            border: "1px solid var(--line)",
            background: "rgba(255, 255, 255, 0.76)",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.3fr) repeat(2, minmax(160px, 0.6fr))",
              gap: "12px",
            }}
          >
            <input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Marka, sube, yetkili veya unvan ara"
              style={fieldStyle}
            />
            <select
              value={filterPricingModel}
              onChange={(event) => setFilterPricingModel(event.target.value)}
              style={fieldStyle}
            >
              <option value="">Tum Modeller</option>
              {options?.pricing_models.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <select
              value={filterStatus}
              onChange={(event) => setFilterStatus(event.target.value as "all" | "active" | "passive")}
              style={fieldStyle}
            >
              <option value="all">Tum Durumlar</option>
              <option value="active">Aktif</option>
              <option value="passive">Pasif</option>
            </select>
          </div>

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
              <div style={{ color: "var(--muted)" }}>Restoran listesi yukleniyor...</div>
            ) : listError ? (
              <div style={{ color: "#b53632" }}>{listError}</div>
            ) : !entries.length ? (
              <div style={{ color: "var(--muted)" }}>Filtreye uyan restoran kaydi bulunamadi.</div>
            ) : (
              entries.map((entry) => (
                <button
                  type="button"
                  key={entry.id}
                  onClick={() => setSelectedEntryId(entry.id)}
                  style={{
                    textAlign: "left",
                    padding: "16px",
                    borderRadius: "18px",
                    border:
                      entry.id === selectedEntryId
                        ? "1px solid rgba(15, 95, 215, 0.28)"
                        : "1px solid rgba(193, 209, 232, 0.9)",
                    background:
                      entry.id === selectedEntryId
                        ? "rgba(15, 95, 215, 0.08)"
                        : "rgba(255, 255, 255, 0.92)",
                    cursor: "pointer",
                    display: "grid",
                    gap: "10px",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", alignItems: "center" }}>
                    <div>
                      <div style={{ fontWeight: 900 }}>{entry.brand} - {entry.branch}</div>
                      <div style={{ color: "var(--muted)", marginTop: "4px" }}>{entry.pricing_model_label}</div>
                    </div>
                    <span
                      style={{
                        display: "inline-flex",
                        padding: "6px 10px",
                        borderRadius: "999px",
                        fontSize: "0.76rem",
                        fontWeight: 800,
                        color: entry.active ? "#0f5fd7" : "#7b879c",
                        background: entry.active ? "rgba(15, 95, 215, 0.1)" : "rgba(95, 118, 152, 0.1)",
                        border: entry.active
                          ? "1px solid rgba(15, 95, 215, 0.14)"
                          : "1px solid rgba(95, 118, 152, 0.12)",
                      }}
                    >
                      {entry.active ? "Aktif" : "Pasif"}
                    </span>
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                      gap: "10px",
                      color: "var(--muted)",
                      fontSize: "0.9rem",
                    }}
                  >
                    <div>Yetkili: {entry.contact_name || "-"}</div>
                    <div>Kadro: {entry.target_headcount}</div>
                    <div>
                      {entry.pricing_model === "fixed_monthly"
                        ? formatCurrency(entry.fixed_monthly_fee)
                        : formatCurrency(entry.hourly_rate)}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
          <div style={{ color: "var(--muted)", fontSize: "0.92rem" }}>
            Toplam {totalEntries} restoran kaydi.
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          style={{
            display: "grid",
            gap: "14px",
            padding: "18px",
            borderRadius: "20px",
            border: "1px solid var(--line)",
            background: "rgba(255, 255, 255, 0.86)",
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
            <div>
              <div style={{ fontSize: "1rem", fontWeight: 900 }}>Secili Kart</div>
              <div style={{ color: "var(--muted)", marginTop: "4px" }}>
                {selectedEntry ? `${selectedEntry.brand} - ${selectedEntry.branch}` : "Restoran sec"}
              </div>
            </div>
            <span
              style={{
                display: "inline-flex",
                padding: "6px 10px",
                borderRadius: "999px",
                fontSize: "0.76rem",
                fontWeight: 800,
                color: "var(--accent)",
                background: "rgba(15, 95, 215, 0.1)",
                border: "1px solid rgba(15, 95, 215, 0.14)",
              }}
            >
              {selectedPricingLabel || "-"}
            </span>
          </div>

          {detailLoading ? (
            <div style={{ color: "var(--muted)" }}>Detay yukleniyor...</div>
          ) : selectedEntry ? (
            <>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  gap: "12px",
                }}
              >
                <input value={editBrand} onChange={(event) => setEditBrand(event.target.value)} placeholder="Marka" style={fieldStyle} />
                <input value={editBranch} onChange={(event) => setEditBranch(event.target.value)} placeholder="Sube" style={fieldStyle} />
                <select value={editPricingModel} onChange={(event) => setEditPricingModel(event.target.value)} style={fieldStyle}>
                  {options?.pricing_models.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
                <select value={editStatus} onChange={(event) => setEditStatus(event.target.value)} style={fieldStyle}>
                  {options?.status_options.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
                <input value={editTargetHeadcount} onChange={(event) => setEditTargetHeadcount(event.target.value)} placeholder="Hedef Kadro" style={fieldStyle} />
                <input value={editVatRate} onChange={(event) => setEditVatRate(event.target.value)} placeholder="KDV %" style={fieldStyle} />
                <input type="date" value={editStartDate} onChange={(event) => setEditStartDate(event.target.value)} style={fieldStyle} />
                <input type="date" value={editEndDate} onChange={(event) => setEditEndDate(event.target.value)} style={fieldStyle} />
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
                  gap: "12px",
                }}
              >
                {editPricingModel === "hourly_plus_package" && (
                  <>
                    <input value={editHourlyRate} onChange={(event) => setEditHourlyRate(event.target.value)} placeholder="Saatlik Ucret" style={fieldStyle} />
                    <input value={editPackageRate} onChange={(event) => setEditPackageRate(event.target.value)} placeholder="Paket Primi" style={fieldStyle} />
                  </>
                )}

                {editPricingModel === "threshold_package" && (
                  <>
                    <input value={editHourlyRate} onChange={(event) => setEditHourlyRate(event.target.value)} placeholder="Saatlik Ucret" style={fieldStyle} />
                    <input value={editPackageThreshold} onChange={(event) => setEditPackageThreshold(event.target.value)} placeholder="Paket Esigi" style={fieldStyle} />
                    <input value={editPackageRateLow} onChange={(event) => setEditPackageRateLow(event.target.value)} placeholder="Esik Alti Prim" style={fieldStyle} />
                    <input value={editPackageRateHigh} onChange={(event) => setEditPackageRateHigh(event.target.value)} placeholder="Esik Ustu Prim" style={fieldStyle} />
                  </>
                )}

                {editPricingModel === "hourly_only" && (
                  <input value={editHourlyRate} onChange={(event) => setEditHourlyRate(event.target.value)} placeholder="Saatlik Ucret" style={fieldStyle} />
                )}

                {editPricingModel === "fixed_monthly" && (
                  <input value={editFixedMonthlyFee} onChange={(event) => setEditFixedMonthlyFee(event.target.value)} placeholder="Sabit Aylik Ucret" style={fieldStyle} />
                )}
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  gap: "12px",
                }}
              >
                <input value={editContactName} onChange={(event) => setEditContactName(event.target.value)} placeholder="Yetkili Ad Soyad" style={fieldStyle} />
                <input value={editContactPhone} onChange={(event) => setEditContactPhone(event.target.value)} placeholder="Yetkili Telefon" style={fieldStyle} />
                <input value={editContactEmail} onChange={(event) => setEditContactEmail(event.target.value)} placeholder="Yetkili E-posta" style={fieldStyle} />
                <input value={editCompanyTitle} onChange={(event) => setEditCompanyTitle(event.target.value)} placeholder="Unvan" style={fieldStyle} />
                <input value={editTaxOffice} onChange={(event) => setEditTaxOffice(event.target.value)} placeholder="Vergi Dairesi" style={fieldStyle} />
                <input value={editTaxNumber} onChange={(event) => setEditTaxNumber(event.target.value)} placeholder="Vergi Numarasi" style={fieldStyle} />
              </div>

              <textarea
                value={editAddress}
                onChange={(event) => setEditAddress(event.target.value)}
                placeholder="Adres"
                rows={2}
                style={{ ...fieldStyle, resize: "vertical" }}
              />

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  gap: "12px",
                }}
              >
                <input value={editExtraHeadcountRequest} onChange={(event) => setEditExtraHeadcountRequest(event.target.value)} placeholder="Ek Kurye Talebi" style={fieldStyle} />
                <input type="date" value={editExtraHeadcountRequestDate} onChange={(event) => setEditExtraHeadcountRequestDate(event.target.value)} style={fieldStyle} />
                <input value={editReduceHeadcountRequest} onChange={(event) => setEditReduceHeadcountRequest(event.target.value)} placeholder="Kurye Azaltma Talebi" style={fieldStyle} />
                <input type="date" value={editReduceHeadcountRequestDate} onChange={(event) => setEditReduceHeadcountRequestDate(event.target.value)} style={fieldStyle} />
              </div>

              <textarea
                value={editNotes}
                onChange={(event) => setEditNotes(event.target.value)}
                placeholder="Not"
                rows={3}
                style={{ ...fieldStyle, resize: "vertical" }}
              />

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

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                  gap: "10px",
                }}
              >
                <button
                  type="submit"
                  disabled={isPending}
                  style={actionButton("primary")}
                >
                  {isPending ? "Kaydediliyor..." : "Guncelle"}
                </button>
                <button type="button" onClick={handleToggleStatus} style={actionButton("soft")}>
                  {selectedEntry.active ? "Pasife Al" : "Aktiflestir"}
                </button>
                <button type="button" onClick={handleDelete} style={actionButton("danger")}>
                  Kalici Sil
                </button>
              </div>
            </>
          ) : (
            <div style={{ color: "var(--muted)" }}>Detay formu icin soldan restoran sec.</div>
          )}
        </form>
      </div>
    </section>
  );
}

function actionButton(kind: "primary" | "soft" | "danger"): CSSProperties {
  const styles = {
    primary: {
      background: "var(--accent)",
      color: "#fff",
      border: "none",
    },
    soft: {
      background: "rgba(15, 95, 215, 0.08)",
      color: "var(--accent)",
      border: "1px solid rgba(15, 95, 215, 0.16)",
    },
    danger: {
      background: "rgba(205, 70, 66, 0.08)",
      color: "#b53632",
      border: "1px solid rgba(205, 70, 66, 0.16)",
    },
  }[kind];
  return {
    padding: "14px 16px",
    borderRadius: "16px",
    fontWeight: 800,
    cursor: "pointer",
    ...styles,
  };
}
