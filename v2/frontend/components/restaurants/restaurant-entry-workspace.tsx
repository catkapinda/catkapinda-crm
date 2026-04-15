"use client";

import type { CSSProperties, FormEvent } from "react";
import { useMemo, useState, useTransition, useEffect } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type RestaurantPricingModelOption = {
  value: string;
  label: string;
};

type RestaurantsFormOptions = {
  pricing_models: RestaurantPricingModelOption[];
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

export function RestaurantEntryWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<RestaurantsFormOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");

  const [brand, setBrand] = useState("");
  const [branch, setBranch] = useState("");
  const [pricingModel, setPricingModel] = useState("hourly_plus_package");
  const [status, setStatus] = useState("Aktif");
  const [hourlyRate, setHourlyRate] = useState("0");
  const [packageRate, setPackageRate] = useState("0");
  const [packageThreshold, setPackageThreshold] = useState("390");
  const [packageRateLow, setPackageRateLow] = useState("0");
  const [packageRateHigh, setPackageRateHigh] = useState("0");
  const [fixedMonthlyFee, setFixedMonthlyFee] = useState("0");
  const [vatRate, setVatRate] = useState("20");
  const [targetHeadcount, setTargetHeadcount] = useState("1");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState("");
  const [extraHeadcountRequest, setExtraHeadcountRequest] = useState("0");
  const [extraHeadcountRequestDate, setExtraHeadcountRequestDate] = useState("");
  const [reduceHeadcountRequest, setReduceHeadcountRequest] = useState("0");
  const [reduceHeadcountRequestDate, setReduceHeadcountRequestDate] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [companyTitle, setCompanyTitle] = useState("");
  const [address, setAddress] = useState("");
  const [taxOffice, setTaxOffice] = useState("");
  const [taxNumber, setTaxNumber] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    async function loadOptions() {
      setLoadingOptions(true);
      try {
        const response = await apiFetch("/restaurants/form-options");
        if (!response.ok) {
          throw new Error("Restoran form secenekleri yuklenemedi.");
        }
        const payload = (await response.json()) as RestaurantsFormOptions;
        setOptions(payload);
        setPricingModel(payload.selected_pricing_model);
        setStatus(payload.status_options[0] ?? "Aktif");
      } catch (error) {
        setSubmitError(
          error instanceof Error ? error.message : "Restoran form secenekleri yuklenemedi.",
        );
      } finally {
        setLoadingOptions(false);
      }
    }

    void loadOptions();
  }, []);

  const pricingLabel = useMemo(
    () => options?.pricing_models.find((item) => item.value === pricingModel)?.label ?? pricingModel,
    [options, pricingModel],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    const response = await apiFetch("/restaurants/records", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        brand,
        branch,
        pricing_model: pricingModel,
        hourly_rate: Number(hourlyRate || 0),
        package_rate: Number(packageRate || 0),
        package_threshold: Number(packageThreshold || 390),
        package_rate_low: Number(packageRateLow || 0),
        package_rate_high: Number(packageRateHigh || 0),
        fixed_monthly_fee: Number(fixedMonthlyFee || 0),
        vat_rate: Number(vatRate || 20),
        target_headcount: Number(targetHeadcount || 0),
        start_date: startDate || null,
        end_date: endDate || null,
        extra_headcount_request: Number(extraHeadcountRequest || 0),
        extra_headcount_request_date: extraHeadcountRequestDate || null,
        reduce_headcount_request: Number(reduceHeadcountRequest || 0),
        reduce_headcount_request_date: reduceHeadcountRequestDate || null,
        contact_name: contactName,
        contact_phone: contactPhone,
        contact_email: contactEmail,
        company_title: companyTitle,
        address,
        tax_office: taxOffice,
        tax_number: taxNumber,
        status,
        notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;

    if (!response.ok) {
      setSubmitError(payload?.detail || "Restoran kaydı oluşturulamadı.");
      return;
    }

    setSubmitSuccess(payload?.message || "Restoran kaydı oluşturuldu.");
    setBrand("");
    setBranch("");
    setContactName("");
    setContactPhone("");
    setContactEmail("");
    setCompanyTitle("");
    setAddress("");
    setTaxOffice("");
    setTaxNumber("");
    setNotes("");
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Yeni Restoran Kaydı</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Marka, fiyat modeli ve vergi bilgilerini yeni shell içinde daha hızlı kaydet.
        </p>
      </div>

      {loadingOptions ? (
        <div
          style={{
            padding: "18px",
            borderRadius: "18px",
            background: "rgba(15, 95, 215, 0.06)",
            color: "var(--muted)",
          }}
        >
          Restoran form secenekleri yükleniyor...
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "16px" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.45fr) minmax(280px, 360px)",
              gap: "16px",
              alignItems: "start",
            }}
          >
            <div style={{ display: "grid", gap: "14px" }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Marka</span>
                  <input value={brand} onChange={(event) => setBrand(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Şube</span>
                  <input value={branch} onChange={(event) => setBranch(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Fiyat Modeli</span>
                  <select
                    value={pricingModel}
                    onChange={(event) => setPricingModel(event.target.value)}
                    style={fieldStyle}
                  >
                    {options?.pricing_models.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Durum</span>
                  <select value={status} onChange={(event) => setStatus(event.target.value)} style={fieldStyle}>
                    {options?.status_options.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Hedef Kadro</span>
                  <input
                    inputMode="numeric"
                    value={targetHeadcount}
                    onChange={(event) => setTargetHeadcount(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>KDV %</span>
                  <input value={vatRate} onChange={(event) => setVatRate(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Baslangic Tarihi</span>
                  <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Bitis Tarihi</span>
                  <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} style={fieldStyle} />
                </label>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
                  gap: "14px",
                }}
              >
                {pricingModel === "hourly_plus_package" && (
                  <>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Saatlik Ucret</span>
                      <input value={hourlyRate} onChange={(event) => setHourlyRate(event.target.value)} style={fieldStyle} />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Paket Primi</span>
                      <input value={packageRate} onChange={(event) => setPackageRate(event.target.value)} style={fieldStyle} />
                    </label>
                  </>
                )}

                {pricingModel === "threshold_package" && (
                  <>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Saatlik Ucret</span>
                      <input value={hourlyRate} onChange={(event) => setHourlyRate(event.target.value)} style={fieldStyle} />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Paket Esigi</span>
                      <input
                        value={packageThreshold}
                        onChange={(event) => setPackageThreshold(event.target.value)}
                        style={fieldStyle}
                      />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Esik Alti Prim</span>
                      <input
                        value={packageRateLow}
                        onChange={(event) => setPackageRateLow(event.target.value)}
                        style={fieldStyle}
                      />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Esik Ustu Prim</span>
                      <input
                        value={packageRateHigh}
                        onChange={(event) => setPackageRateHigh(event.target.value)}
                        style={fieldStyle}
                      />
                    </label>
                  </>
                )}

                {pricingModel === "hourly_only" && (
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Saatlik Ucret</span>
                    <input value={hourlyRate} onChange={(event) => setHourlyRate(event.target.value)} style={fieldStyle} />
                  </label>
                )}

                {pricingModel === "fixed_monthly" && (
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Sabit Aylık Ucret</span>
                    <input
                      value={fixedMonthlyFee}
                      onChange={(event) => setFixedMonthlyFee(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                )}
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Yetkili Ad Soyad</span>
                  <input value={contactName} onChange={(event) => setContactName(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Yetkili Telefon</span>
                  <input value={contactPhone} onChange={(event) => setContactPhone(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Yetkili E-posta</span>
                  <input value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Unvan</span>
                  <input value={companyTitle} onChange={(event) => setCompanyTitle(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Vergi Dairesi</span>
                  <input value={taxOffice} onChange={(event) => setTaxOffice(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Vergi Numarasi</span>
                  <input value={taxNumber} onChange={(event) => setTaxNumber(event.target.value)} style={fieldStyle} />
                </label>
              </div>

              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Adres</span>
                <textarea
                  value={address}
                  onChange={(event) => setAddress(event.target.value)}
                  rows={2}
                  style={{ ...fieldStyle, resize: "vertical" }}
                />
              </label>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Ek Kurye Talep Sayisi</span>
                  <input
                    value={extraHeadcountRequest}
                    onChange={(event) => setExtraHeadcountRequest(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Ek Kurye Talep Tarihi</span>
                  <input
                    type="date"
                    value={extraHeadcountRequestDate}
                    onChange={(event) => setExtraHeadcountRequestDate(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Kurye Azaltma Sayisi</span>
                  <input
                    value={reduceHeadcountRequest}
                    onChange={(event) => setReduceHeadcountRequest(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Kurye Azaltma Tarihi</span>
                  <input
                    type="date"
                    value={reduceHeadcountRequestDate}
                    onChange={(event) => setReduceHeadcountRequestDate(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
              </div>

              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Not</span>
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  rows={3}
                  style={{ ...fieldStyle, resize: "vertical" }}
                />
              </label>

              <button
                type="submit"
                disabled={isPending}
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
                {isPending ? "Kaydediliyor..." : "Restoran Kaydini Oluştur"}
              </button>
            </div>

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
              <h3 style={{ margin: 0, fontSize: "1rem" }}>Kayıt Ozeti</h3>
              <SummaryItem label="Şube" value={brand && branch ? `${brand} - ${branch}` : "-"} />
              <SummaryItem label="Model" value={pricingLabel} />
              <SummaryItem label="Durum" value={status} />
              <SummaryItem label="Hedef Kadro" value={targetHeadcount} />
              <SummaryItem
                label="Faturalama"
                value={
                  pricingModel === "fixed_monthly"
                    ? formatCurrency(Number(fixedMonthlyFee || 0))
                    : formatCurrency(Number(hourlyRate || 0))
                }
              />
              <SummaryItem label="Yetkili" value={contactName || "-"} />
            </aside>
          </div>

          {(submitError || submitSuccess) && (
            <div
              style={{
                padding: "14px 16px",
                borderRadius: "16px",
                border: submitError ? "1px solid rgba(205, 70, 66, 0.18)" : "1px solid rgba(35, 148, 94, 0.18)",
                background: submitError ? "rgba(205, 70, 66, 0.08)" : "rgba(35, 148, 94, 0.08)",
                color: submitError ? "#b53632" : "#1d7b4d",
                fontWeight: 700,
              }}
            >
              {submitError || submitSuccess}
            </div>
          )}
        </form>
      )}
    </section>
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
        background: "rgba(255, 255, 255, 0.9)",
      }}
    >
      <div
        style={{
          color: "var(--muted)",
          fontSize: "0.76rem",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          fontWeight: 800,
        }}
      >
        {label}
      </div>
      <div style={{ fontWeight: 800 }}>{value}</div>
    </div>
  );
}
