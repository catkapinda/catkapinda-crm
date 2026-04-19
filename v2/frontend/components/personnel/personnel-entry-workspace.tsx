"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";
import { useAuth } from "../../components/auth/auth-provider";

type PersonnelFormOptions = {
  restaurants: Array<{
    id: number;
    label: string;
  }>;
  role_options: string[];
  status_options: string[];
  vehicle_mode_options: string[];
  accounting_type_options: string[];
  company_setup_options: string[];
  selected_restaurant_id: number | null;
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

function normalizeLookupText(value: string) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[ıİ]/g, "i")
    .toLowerCase();
}

function vehicleModeKind(value: string) {
  const normalized = normalizeLookupText(value);
  if (normalized.includes("cat kapinda") && normalized.includes("kirasi")) {
    return "rental";
  }
  if (normalized.includes("cat kapinda") && normalized.includes("satisi")) {
    return "sale";
  }
  return "own";
}

function formatCurrency(value: string | number) {
  return new Intl.NumberFormat("tr-TR", {
    style: "currency",
    currency: "TRY",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

export function PersonnelEntryWorkspace() {
  const router = useRouter();
  const { user } = useAuth();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<PersonnelFormOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const [generatedCode, setGeneratedCode] = useState("");

  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("Kurye");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [iban, setIban] = useState("");
  const [taxNumber, setTaxNumber] = useState("");
  const [taxOffice, setTaxOffice] = useState("");
  const [emergencyContactName, setEmergencyContactName] = useState("");
  const [emergencyContactPhone, setEmergencyContactPhone] = useState("");
  const [accountingType, setAccountingType] = useState("Kendi Muhasebecisi");
  const [newCompanySetup, setNewCompanySetup] = useState("Hayır");
  const [accountingRevenue, setAccountingRevenue] = useState("0");
  const [accountantCost, setAccountantCost] = useState("0");
  const [companySetupRevenue, setCompanySetupRevenue] = useState("0");
  const [companySetupCost, setCompanySetupCost] = useState("0");
  const [restaurantId, setRestaurantId] = useState<number | "">("");
  const [status, setStatus] = useState("Aktif");
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [vehicleMode, setVehicleMode] = useState("Kendi Motoru");
  const [currentPlate, setCurrentPlate] = useState("");
  const [motorRentalMonthlyAmount, setMotorRentalMonthlyAmount] = useState("13000");
  const [motorPurchaseStartDate, setMotorPurchaseStartDate] = useState("");
  const [motorPurchaseCommitmentMonths, setMotorPurchaseCommitmentMonths] = useState("0");
  const [motorPurchaseSalePrice, setMotorPurchaseSalePrice] = useState("0");
  const [motorPurchaseMonthlyDeduction, setMotorPurchaseMonthlyDeduction] = useState("0");
  const [monthlyFixedCost, setMonthlyFixedCost] = useState("0");
  const [notes, setNotes] = useState("");
  const canViewPlateArea = user?.allowed_actions.includes("personnel.plate") ?? false;
  const currentVehicleModeKind = vehicleModeKind(vehicleMode);
  const isRentalVehicle = currentVehicleModeKind === "rental";
  const isSaleVehicle = currentVehicleModeKind === "sale";
  const isCatKapindaVehicle = currentVehicleModeKind !== "own";

  useEffect(() => {
    async function loadOptions() {
      setLoadingOptions(true);
      try {
        const response = await apiFetch("/personnel/form-options");
        if (!response.ok) {
          throw new Error("Personel form seçenekleri alınamadı.");
        }
        const payload = (await response.json()) as PersonnelFormOptions;
        setOptions(payload);
        setRole(payload.role_options[0] ?? "Kurye");
        setStatus(payload.status_options[0] ?? "Aktif");
        setVehicleMode(payload.vehicle_mode_options[0] ?? "Kendi Motoru");
        setAccountingType(payload.accounting_type_options?.[0] ?? "Kendi Muhasebecisi");
        setNewCompanySetup(payload.company_setup_options?.[0] ?? "Hayır");
        setRestaurantId(payload.selected_restaurant_id ?? "");
      } catch (error) {
        setSubmitError(
          error instanceof Error ? error.message : "Personel form seçenekleri alınamadı.",
        );
      } finally {
        setLoadingOptions(false);
      }
    }

    void loadOptions();
  }, []);

  const selectedRestaurantLabel = useMemo(() => {
    if (!options || typeof restaurantId !== "number") {
      return "Atanmadı";
    }
    return options.restaurants.find((restaurant) => restaurant.id === restaurantId)?.label ?? "Atanmadı";
  }, [options, restaurantId]);

  function handleVehicleModeChange(nextVehicleMode: string) {
    setVehicleMode(nextVehicleMode);
    const nextKind = vehicleModeKind(nextVehicleMode);
    if (nextKind !== "own") {
      setMotorPurchaseStartDate((current) => current || startDate);
      setMotorPurchaseCommitmentMonths((current) => (Number(current || 0) > 0 ? current : "12"));
    }
    if (nextKind === "rental") {
      setMotorRentalMonthlyAmount((current) => (Number(current || 0) > 0 ? current : "13000"));
      setMotorPurchaseSalePrice("0");
      setMotorPurchaseMonthlyDeduction("0");
    }
    if (nextKind === "sale") {
      setMotorRentalMonthlyAmount("0");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError("");
    setSubmitSuccess("");
    setGeneratedCode("");

    if (!fullName.trim()) {
      setSubmitError("Ad soyad zorunlu.");
      return;
    }

    const response = await apiFetch("/personnel/records", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        full_name: fullName,
        role,
        phone,
        address,
        iban,
        tax_number: taxNumber,
        tax_office: taxOffice,
        emergency_contact_name: emergencyContactName,
        emergency_contact_phone: emergencyContactPhone,
        accounting_type: accountingType,
        new_company_setup: newCompanySetup,
        accounting_revenue: Number(accountingRevenue || 0),
        accountant_cost: Number(accountantCost || 0),
        company_setup_revenue: Number(companySetupRevenue || 0),
        company_setup_cost: Number(companySetupCost || 0),
        assigned_restaurant_id: typeof restaurantId === "number" ? restaurantId : null,
        status,
        start_date: startDate || null,
        vehicle_mode: vehicleMode,
        current_plate: currentPlate,
        motor_rental_monthly_amount: Number(motorRentalMonthlyAmount || 0),
        motor_purchase_start_date: motorPurchaseStartDate || null,
        motor_purchase_commitment_months: Number(motorPurchaseCommitmentMonths || 0),
        motor_purchase_sale_price: Number(motorPurchaseSalePrice || 0),
        motor_purchase_monthly_deduction: Number(motorPurchaseMonthlyDeduction || 0),
        monthly_fixed_cost: Number(monthlyFixedCost || 0),
        notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string; person_code?: string }
      | null;

    if (!response.ok) {
      setSubmitError(payload?.detail || "Personel kaydı oluşturulamadı.");
      return;
    }

    setSubmitSuccess(payload?.message || "Personel kaydı oluşturuldu.");
    setGeneratedCode(payload?.person_code || "");
    setFullName("");
    setPhone("");
    setAddress("");
    setIban("");
    setTaxNumber("");
    setTaxOffice("");
    setEmergencyContactName("");
    setEmergencyContactPhone("");
    setAccountingType(options?.accounting_type_options?.[0] ?? "Kendi Muhasebecisi");
    setNewCompanySetup(options?.company_setup_options?.[0] ?? "Hayır");
    setAccountingRevenue("0");
    setAccountantCost("0");
    setCompanySetupRevenue("0");
    setCompanySetupCost("0");
    setCurrentPlate("");
    setMotorRentalMonthlyAmount("13000");
    setMotorPurchaseStartDate("");
    setMotorPurchaseCommitmentMonths("0");
    setMotorPurchaseSalePrice("0");
    setMotorPurchaseMonthlyDeduction("0");
    setMonthlyFixedCost("0");
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Personel Kaydı</h2>
        <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.7 }}>
          Personelin operasyon, finans ve acil durum bilgilerini tek temiz kartta oluştur.
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
          Personel form seçenekleri yükleniyor...
        </div>
      ) : (
        <form
          onSubmit={handleSubmit}
          style={{
            display: "grid",
            gap: "16px",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.5fr) minmax(280px, 360px)",
              gap: "16px",
              alignItems: "start",
            }}
          >
            <div
              style={{
                display: "grid",
                gap: "14px",
              }}
            >
              <SectionHeader title="Temel Bilgiler" />
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Ad Soyad</span>
                  <input
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    placeholder="Örn. Ali Yılmaz"
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Rol</span>
                  <select value={role} onChange={(event) => setRole(event.target.value)} style={fieldStyle}>
                    {options?.role_options.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Telefon</span>
                  <input
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    placeholder="05xxxxxxxxx"
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Adres</span>
                  <input value={address} onChange={(event) => setAddress(event.target.value)} style={fieldStyle} />
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
                  <span style={{ fontWeight: 700 }}>Restoran / Şube</span>
                  <select
                    value={restaurantId}
                    onChange={(event) =>
                      setRestaurantId(event.target.value ? Number(event.target.value) : "")
                    }
                    style={fieldStyle}
                  >
                    <option value="">Atanmadı</option>
                    {options?.restaurants.map((restaurant) => (
                      <option key={restaurant.id} value={restaurant.id}>
                        {restaurant.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>İşe Giriş</span>
                  <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} style={fieldStyle} />
                </label>
                {canViewPlateArea ? (
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Araç Modu</span>
                    <select value={vehicleMode} onChange={(event) => handleVehicleModeChange(event.target.value)} style={fieldStyle}>
                      {options?.vehicle_mode_options.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
                {canViewPlateArea ? (
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Plaka</span>
                    <input value={currentPlate} onChange={(event) => setCurrentPlate(event.target.value)} style={fieldStyle} />
                  </label>
                ) : null}
                {canViewPlateArea && isRentalVehicle ? (
                  <label style={{ display: "grid", gap: "8px" }}>
                    <span style={{ fontWeight: 700 }}>Aylık Motor Kirası</span>
                    <input
                      inputMode="decimal"
                      value={motorRentalMonthlyAmount}
                      onChange={(event) => setMotorRentalMonthlyAmount(event.target.value)}
                      style={fieldStyle}
                    />
                  </label>
                ) : null}
                {canViewPlateArea && isCatKapindaVehicle ? (
                  <>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Motor Başlangıcı</span>
                      <input
                        type="date"
                        value={motorPurchaseStartDate}
                        onChange={(event) => setMotorPurchaseStartDate(event.target.value)}
                        style={fieldStyle}
                      />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Ay Taahhüdü</span>
                      <input
                        inputMode="numeric"
                        value={motorPurchaseCommitmentMonths}
                        onChange={(event) => setMotorPurchaseCommitmentMonths(event.target.value)}
                        style={fieldStyle}
                      />
                    </label>
                  </>
                ) : null}
                {canViewPlateArea && isSaleVehicle ? (
                  <>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Motor Satış Tutarı</span>
                      <input
                        inputMode="decimal"
                        value={motorPurchaseSalePrice}
                        onChange={(event) => setMotorPurchaseSalePrice(event.target.value)}
                        style={fieldStyle}
                      />
                    </label>
                    <label style={{ display: "grid", gap: "8px" }}>
                      <span style={{ fontWeight: 700 }}>Aylık Kesinti</span>
                      <input
                        inputMode="decimal"
                        value={motorPurchaseMonthlyDeduction}
                        onChange={(event) => setMotorPurchaseMonthlyDeduction(event.target.value)}
                        style={fieldStyle}
                      />
                    </label>
                  </>
                ) : null}
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Aylık Sabit Tutar</span>
                  <input
                    inputMode="decimal"
                    value={monthlyFixedCost}
                    onChange={(event) => setMonthlyFixedCost(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
              </div>

              <SectionHeader title="Muhasebe Bilgileri" />
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>IBAN</span>
                  <input
                    value={iban}
                    onChange={(event) => setIban(event.target.value)}
                    placeholder="TR..."
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Vergi Numarası</span>
                  <input
                    value={taxNumber}
                    onChange={(event) => setTaxNumber(event.target.value)}
                    placeholder="TCKN / VKN"
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Vergi Dairesi</span>
                  <input value={taxOffice} onChange={(event) => setTaxOffice(event.target.value)} style={fieldStyle} />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Muhasebe</span>
                  <select
                    value={accountingType}
                    onChange={(event) => setAccountingType(event.target.value)}
                    style={fieldStyle}
                  >
                    {(options?.accounting_type_options ?? [accountingType]).map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Yeni Şirket Açılışı</span>
                  <select
                    value={newCompanySetup}
                    onChange={(event) => setNewCompanySetup(event.target.value)}
                    style={fieldStyle}
                  >
                    {(options?.company_setup_options ?? [newCompanySetup]).map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Muhasebe Geliri</span>
                  <input
                    inputMode="decimal"
                    value={accountingRevenue}
                    onChange={(event) => setAccountingRevenue(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Muhasebeci Maliyeti</span>
                  <input
                    inputMode="decimal"
                    value={accountantCost}
                    onChange={(event) => setAccountantCost(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Şirket Açılış Geliri</span>
                  <input
                    inputMode="decimal"
                    value={companySetupRevenue}
                    onChange={(event) => setCompanySetupRevenue(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Şirket Açılış Maliyeti</span>
                  <input
                    inputMode="decimal"
                    value={companySetupCost}
                    onChange={(event) => setCompanySetupCost(event.target.value)}
                    style={fieldStyle}
                  />
                </label>
              </div>

              <SectionHeader title="Acil Durum" />
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "14px",
                }}
              >
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Yakını Ad Soyad</span>
                  <input
                    value={emergencyContactName}
                    onChange={(event) => setEmergencyContactName(event.target.value)}
                    placeholder="Yakının adı soyadı"
                    style={fieldStyle}
                  />
                </label>
                <label style={{ display: "grid", gap: "8px" }}>
                  <span style={{ fontWeight: 700 }}>Yakını Telefon</span>
                  <input
                    value={emergencyContactPhone}
                    onChange={(event) => setEmergencyContactPhone(event.target.value)}
                    placeholder="05xxxxxxxxx"
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
                  style={{ ...fieldStyle, resize: "vertical", minHeight: "96px" }}
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
                {isPending ? "Kaydediliyor..." : "Personel Kaydını Oluştur"}
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
                position: "sticky",
                top: "18px",
              }}
            >
              <h3 style={{ margin: 0, fontSize: "1rem" }}>Kayıt Özeti</h3>
              <SummaryItem label="Rol" value={role} />
              <SummaryItem label="Şube" value={selectedRestaurantLabel} />
              {canViewPlateArea ? <SummaryItem label="Araç" value={vehicleMode} /> : null}
              {canViewPlateArea && isCatKapindaVehicle ? (
                <SummaryItem label="Ay Taahhüdü" value={`${Number(motorPurchaseCommitmentMonths || 0)} ay`} />
              ) : null}
              {canViewPlateArea && isRentalVehicle ? (
                <SummaryItem label="Motor Kirası" value={formatCurrency(motorRentalMonthlyAmount)} />
              ) : null}
              {canViewPlateArea && isSaleVehicle ? (
                <SummaryItem label="Aylık Kesinti" value={formatCurrency(motorPurchaseMonthlyDeduction)} />
              ) : null}
              <SummaryItem label="Durum" value={status} />
              <SummaryItem label="IBAN" value={iban ? "Girildi" : "Eksik"} />
              <SummaryItem
                label="Vergi"
                value={taxNumber || taxOffice ? "Girildi" : "Eksik"}
              />
              <SummaryItem label="Muhasebe" value={accountingType} />
              <SummaryItem label="Şirket Açılışı" value={newCompanySetup} />
              <SummaryItem
                label="Acil Durum"
                value={emergencyContactName || emergencyContactPhone ? "Girildi" : "Eksik"}
              />
              <SummaryItem
                label="Sabit Tutar"
                value={formatCurrency(monthlyFixedCost)}
              />
              {generatedCode ? <SummaryItem label="Oluşan Kod" value={generatedCode} /> : null}
            </aside>
          </div>

          {submitError ? <InlineMessage tone="error" message={submitError} /> : null}
          {submitSuccess ? <InlineMessage tone="success" message={submitSuccess} /> : null}
        </form>
      )}
    </section>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div
      style={{
        paddingTop: "4px",
        color: "var(--accent-strong)",
        fontSize: "0.72rem",
        fontWeight: 900,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
      }}
    >
      {title}
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

function InlineMessage({ tone, message }: { tone: "error" | "success"; message: string }) {
  const palette =
    tone === "error"
      ? {
          background: "rgba(222, 66, 66, 0.09)",
          border: "1px solid rgba(222, 66, 66, 0.18)",
          color: "#b53a3a",
        }
      : {
          background: "rgba(38, 167, 107, 0.1)",
          border: "1px solid rgba(38, 167, 107, 0.16)",
          color: "#167f51",
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
