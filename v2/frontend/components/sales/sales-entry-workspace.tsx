"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

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

function pricingSummary(
  pricingModel: string,
  hourlyRate: string,
  packageRate: string,
  packageThreshold: string,
  packageRateLow: string,
  packageRateHigh: string,
  fixedMonthlyFee: string,
) {
  const toMoney = (value: string) =>
    new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: "TRY",
      maximumFractionDigits: 0,
    }).format(Number(value || 0));

  if (pricingModel === "threshold_package") {
    return `${toMoney(hourlyRate)}/saat | ${packageThreshold || "390"} altı ${toMoney(packageRateLow)} | üstü ${toMoney(packageRateHigh)}`;
  }
  if (pricingModel === "hourly_plus_package") {
    return `${toMoney(hourlyRate)}/saat + ${toMoney(packageRate)}/paket`;
  }
  if (pricingModel === "hourly_only") {
    return `${toMoney(hourlyRate)}/saat`;
  }
  if (pricingModel === "fixed_monthly") {
    return `${toMoney(fixedMonthlyFee)}/ay`;
  }
  return "-";
}

export function SalesEntryWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<SalesFormOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");

  const [restaurantName, setRestaurantName] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [address, setAddress] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [requestedCourierCount, setRequestedCourierCount] = useState("1");
  const [leadSource, setLeadSource] = useState("Mail");
  const [pricingModel, setPricingModel] = useState("hourly_plus_package");
  const [hourlyRate, setHourlyRate] = useState("0");
  const [packageRate, setPackageRate] = useState("0");
  const [packageThreshold, setPackageThreshold] = useState("390");
  const [packageRateLow, setPackageRateLow] = useState("0");
  const [packageRateHigh, setPackageRateHigh] = useState("0");
  const [fixedMonthlyFee, setFixedMonthlyFee] = useState("0");
  const [proposedQuote, setProposedQuote] = useState("0");
  const [status, setStatus] = useState("Yeni Talep");
  const [nextFollowUpDate, setNextFollowUpDate] = useState("");
  const [assignedOwner, setAssignedOwner] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    async function loadOptions() {
      setLoadingOptions(true);
      try {
        const response = await apiFetch("/sales/form-options");
        if (!response.ok) {
          throw new Error("Satış form seçenekleri yüklenemedi.");
        }
        const payload = (await response.json()) as SalesFormOptions;
        setOptions(payload);
        setPricingModel(payload.selected_pricing_model);
        setLeadSource(payload.source_options[0] ?? "Mail");
        setStatus(payload.status_options[0] ?? "Yeni Talep");
      } catch (error) {
        setSubmitError(error instanceof Error ? error.message : "Satış form seçenekleri yüklenemedi.");
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

  const summaryText = useMemo(
    () =>
      pricingSummary(
        pricingModel,
        hourlyRate,
        packageRate,
        packageThreshold,
        packageRateLow,
        packageRateHigh,
        fixedMonthlyFee,
      ),
    [pricingModel, hourlyRate, packageRate, packageThreshold, packageRateLow, packageRateHigh, fixedMonthlyFee],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");

    const response = await apiFetch("/sales/records", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        restaurant_name: restaurantName,
        city,
        district,
        address,
        contact_name: contactName,
        contact_phone: contactPhone,
        contact_email: contactEmail,
        requested_courier_count: Number(requestedCourierCount || 0),
        lead_source: leadSource,
        proposed_quote: Number(proposedQuote || 0),
        pricing_model: pricingModel,
        hourly_rate: Number(hourlyRate || 0),
        package_rate: Number(packageRate || 0),
        package_threshold: Number(packageThreshold || 390),
        package_rate_low: Number(packageRateLow || 0),
        package_rate_high: Number(packageRateHigh || 0),
        fixed_monthly_fee: Number(fixedMonthlyFee || 0),
        status,
        next_follow_up_date: nextFollowUpDate || null,
        assigned_owner: assignedOwner,
        notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;
    if (!response.ok) {
      setSubmitError(payload?.detail || "Satış fırsatı oluşturulamadı.");
      return;
    }

    setSubmitSuccess(payload?.message || "Satış fırsatı oluşturuldu.");
    setRestaurantName("");
    setAddress("");
    setContactName("");
    setContactPhone("");
    setContactEmail("");
    setAssignedOwner("");
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Yeni Satış Fırsatı</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Talep kanalı, teklif modeli ve takip bilgisini kaydet.
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
          Satış form seçenekleri yükleniyor...
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
                  <span style={{ fontWeight: 700 }}>Restoran Adı</span>
                  <input value={restaurantName} onChange={(event) => setRestaurantName(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Talep Yeri</span>
                  <select value={leadSource} onChange={(event) => setLeadSource(event.target.value)} style={fieldStyle}>
                    {options?.source_options.map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>İl</span>
                  <input value={city} onChange={(event) => setCity(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>İlçe</span>
                  <input value={district} onChange={(event) => setDistrict(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Talep Edilen Kurye Sayısı</span>
                  <input value={requestedCourierCount} onChange={(event) => setRequestedCourierCount(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Durum</span>
                  <select value={status} onChange={(event) => setStatus(event.target.value)} style={fieldStyle}>
                    {options?.status_options.map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                </label>
              </div>

              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Adres</span>
                <textarea value={address} onChange={(event) => setAddress(event.target.value)} rows={3} style={{ ...fieldStyle, resize: "vertical" }} />
              </label>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Yetkili</span>
                  <input value={contactName} onChange={(event) => setContactName(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Yetkili Telefon</span>
                  <input value={contactPhone} onChange={(event) => setContactPhone(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Mail</span>
                  <input value={contactEmail} onChange={(event) => setContactEmail(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>İlgilenen Kişi</span>
                  <input value={assignedOwner} onChange={(event) => setAssignedOwner(event.target.value)} style={fieldStyle} />
                </label>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Teklif Modeli</span>
                  <select value={pricingModel} onChange={(event) => setPricingModel(event.target.value)} style={fieldStyle}>
                    {options?.pricing_models.map((item) => (
                      <option key={item.value} value={item.value}>{item.label}</option>
                    ))}
                  </select>
                </label>

                {pricingModel === "hourly_plus_package" && (
                  <>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Saatlik Ücret</span>
                      <input value={hourlyRate} onChange={(event) => setHourlyRate(event.target.value)} style={fieldStyle} />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Paket Ücreti</span>
                      <input value={packageRate} onChange={(event) => setPackageRate(event.target.value)} style={fieldStyle} />
                    </label>
                  </>
                )}

                {pricingModel === "threshold_package" && (
                  <>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Saatlik Ücret</span>
                      <input value={hourlyRate} onChange={(event) => setHourlyRate(event.target.value)} style={fieldStyle} />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Eşik</span>
                      <input value={packageThreshold} onChange={(event) => setPackageThreshold(event.target.value)} style={fieldStyle} />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Eşik Altı</span>
                      <input value={packageRateLow} onChange={(event) => setPackageRateLow(event.target.value)} style={fieldStyle} />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Eşik Üstü</span>
                      <input value={packageRateHigh} onChange={(event) => setPackageRateHigh(event.target.value)} style={fieldStyle} />
                    </label>
                  </>
                )}

                {pricingModel === "hourly_only" && (
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Saatlik Ücret</span>
                    <input value={hourlyRate} onChange={(event) => setHourlyRate(event.target.value)} style={fieldStyle} />
                  </label>
                )}

                {pricingModel === "fixed_monthly" && (
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Aylık Tutar</span>
                    <input value={fixedMonthlyFee} onChange={(event) => setFixedMonthlyFee(event.target.value)} style={fieldStyle} />
                  </label>
                )}

                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Önerilen Teklif</span>
                  <input value={proposedQuote} onChange={(event) => setProposedQuote(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Takip Tarihi</span>
                  <input type="date" value={nextFollowUpDate} onChange={(event) => setNextFollowUpDate(event.target.value)} style={fieldStyle} />
                </label>
              </div>

              <label style={{ display: "grid", gap: "8px" }}>
                <span style={{ fontWeight: 700 }}>Notlar</span>
                <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} style={{ ...fieldStyle, resize: "vertical" }} />
              </label>
            </div>

            <aside
              style={{
                padding: "18px",
                borderRadius: "22px",
                border: "1px solid rgba(15, 95, 215, 0.14)",
                background: "rgba(15, 95, 215, 0.05)",
                display: "grid",
                gap: "12px",
              }}
            >
              <div style={{ fontSize: "0.82rem", letterSpacing: "0.05em", textTransform: "uppercase", color: "var(--accent)", fontWeight: 800 }}>
                Teklif Özeti
              </div>
              <div>
                <div style={{ color: "var(--muted)", fontSize: "0.85rem" }}>Model</div>
                <div style={{ marginTop: "4px", fontWeight: 800 }}>{pricingLabel}</div>
              </div>
              <div>
                <div style={{ color: "var(--muted)", fontSize: "0.85rem" }}>Açılım</div>
                <div style={{ marginTop: "4px", fontWeight: 700, lineHeight: 1.6 }}>{summaryText}</div>
              </div>
              <div>
                <div style={{ color: "var(--muted)", fontSize: "0.85rem" }}>Takip</div>
                <div style={{ marginTop: "4px", fontWeight: 700 }}>{status}</div>
              </div>
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

          <button
            type="submit"
            disabled={isPending}
            style={{
              appearance: "none",
              border: "none",
              borderRadius: "18px",
              padding: "14px 18px",
              background: "linear-gradient(135deg, #0f5fd7, #2563eb)",
              color: "white",
              fontWeight: 800,
              letterSpacing: "0.01em",
              cursor: isPending ? "wait" : "pointer",
              boxShadow: "0 18px 40px rgba(15, 95, 215, 0.22)",
            }}
          >
            {isPending ? "Kaydediliyor..." : "Satış Fırsatını Oluştur"}
          </button>
        </form>
      )}
    </section>
  );
}
