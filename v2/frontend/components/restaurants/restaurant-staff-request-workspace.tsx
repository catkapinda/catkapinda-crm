"use client";

import type { CSSProperties, FormEvent } from "react";
import { useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type RestaurantRecord = {
  id: number;
  brand: string;
  branch: string;
  pricing_model: string;
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

type RestaurantsResponse = {
  total_entries: number;
  entries: RestaurantRecord[];
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

export function RestaurantStaffRequestWorkspace() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [entries, setEntries] = useState<RestaurantRecord[]>([]);
  const [selectedRestaurantId, setSelectedRestaurantId] = useState<number | "">("");
  const [extraHeadcountRequest, setExtraHeadcountRequest] = useState("0");
  const [extraHeadcountRequestDate, setExtraHeadcountRequestDate] = useState("");
  const [reduceHeadcountRequest, setReduceHeadcountRequest] = useState("0");
  const [reduceHeadcountRequestDate, setReduceHeadcountRequestDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function loadRestaurants() {
    setLoading(true);
    setError("");
    try {
      const response = await apiFetch("/restaurants/records?limit=400");
      if (!response.ok) {
        throw new Error("Restoran listesi yüklenemedi.");
      }
      const payload = (await response.json()) as RestaurantsResponse;
      setEntries(payload.entries);
      setSelectedRestaurantId((current) => {
        if (current && payload.entries.some((entry) => entry.id === current)) {
          return current;
        }
        return payload.entries[0]?.id ?? "";
      });
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Restoran listesi yüklenemedi.");
      setEntries([]);
      setSelectedRestaurantId("");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadRestaurants();
  }, []);

  const selectedEntry = useMemo(
    () => entries.find((entry) => entry.id === selectedRestaurantId) ?? null,
    [entries, selectedRestaurantId],
  );

  useEffect(() => {
    if (!selectedEntry) {
      setExtraHeadcountRequest("0");
      setExtraHeadcountRequestDate("");
      setReduceHeadcountRequest("0");
      setReduceHeadcountRequestDate("");
      return;
    }
    setExtraHeadcountRequest(String(selectedEntry.extra_headcount_request ?? 0));
    setExtraHeadcountRequestDate(selectedEntry.extra_headcount_request_date ?? "");
    setReduceHeadcountRequest(String(selectedEntry.reduce_headcount_request ?? 0));
    setReduceHeadcountRequestDate(selectedEntry.reduce_headcount_request_date ?? "");
  }, [selectedEntry]);

  const openRequestCount = useMemo(
    () =>
      entries.reduce(
        (sum, entry) =>
          sum + Number(entry.extra_headcount_request || 0) + Number(entry.reduce_headcount_request || 0),
        0,
      ),
    [entries],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSuccess("");

    if (!selectedEntry) {
      setError("Talep girilecek şube seç.");
      return;
    }

    const response = await apiFetch(`/restaurants/records/${selectedEntry.id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        brand: selectedEntry.brand,
        branch: selectedEntry.branch,
        pricing_model: selectedEntry.pricing_model,
        hourly_rate: selectedEntry.hourly_rate,
        package_rate: selectedEntry.package_rate,
        package_threshold: selectedEntry.package_threshold,
        package_rate_low: selectedEntry.package_rate_low,
        package_rate_high: selectedEntry.package_rate_high,
        fixed_monthly_fee: selectedEntry.fixed_monthly_fee,
        vat_rate: selectedEntry.vat_rate,
        target_headcount: selectedEntry.target_headcount,
        start_date: selectedEntry.start_date,
        end_date: selectedEntry.end_date,
        extra_headcount_request: Number(extraHeadcountRequest || 0),
        extra_headcount_request_date: extraHeadcountRequestDate || null,
        reduce_headcount_request: Number(reduceHeadcountRequest || 0),
        reduce_headcount_request_date: reduceHeadcountRequestDate || null,
        contact_name: selectedEntry.contact_name,
        contact_phone: selectedEntry.contact_phone,
        contact_email: selectedEntry.contact_email,
        company_title: selectedEntry.company_title,
        address: selectedEntry.address,
        tax_office: selectedEntry.tax_office,
        tax_number: selectedEntry.tax_number,
        status: selectedEntry.active ? "Aktif" : "Pasif",
        notes: selectedEntry.notes,
      }),
    });

    const payload = (await response.json().catch(() => null)) as { detail?: string; message?: string } | null;
    if (!response.ok) {
      setError(payload?.detail || "Kadro talebi güncellenemedi.");
      return;
    }

    setSuccess(payload?.message || "Kadro talebi güncellendi.");
    await loadRestaurants();
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
        border: "1px solid rgba(15, 95, 215, 0.16)",
        background:
          "linear-gradient(135deg, rgba(248,252,255,0.98), rgba(236,247,244,0.96) 54%, rgba(255,250,241,0.98))",
        boxShadow: "0 18px 44px rgba(20, 39, 67, 0.06)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: "14px",
          alignItems: "flex-start",
          flexWrap: "wrap",
        }}
      >
        <div>
          <div
            style={{
              color: "#0f7a72",
              fontWeight: 900,
              fontSize: "0.72rem",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Kadro Talep Hattı
          </div>
          <h2 style={{ margin: "7px 0 0", fontSize: "1.22rem" }}>Ek kurye ve azaltma talepleri</h2>
          <p style={{ margin: "6px 0 0", color: "var(--muted)", lineHeight: 1.65 }}>
            Restoran kartını kirletmeden, şube bazlı kadro artış ve azaltma ihtiyacını buradan takip et.
          </p>
        </div>
        <div
          style={{
            minWidth: "120px",
            padding: "12px 14px",
            borderRadius: "18px",
            background: "rgba(255,255,255,0.76)",
            border: "1px solid rgba(15,95,215,0.12)",
          }}
        >
          <div style={{ color: "var(--muted)", fontSize: "0.76rem", fontWeight: 800 }}>Açık Talep</div>
          <div style={{ marginTop: "5px", fontSize: "1.35rem", fontWeight: 900 }}>{openRequestCount}</div>
        </div>
      </div>

      {loading ? (
        <InlineMessage tone="soft" message="Kadro talep verileri yükleniyor..." />
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
              gap: "10px",
              alignItems: "end",
            }}
          >
            <label style={{ display: "grid", gap: "7px" }}>
              <span style={{ fontWeight: 800 }}>Şube</span>
              <select
                value={selectedRestaurantId}
                onChange={(event) => setSelectedRestaurantId(event.target.value ? Number(event.target.value) : "")}
                style={fieldStyle}
              >
                {entries.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.brand} - {entry.branch}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: "grid", gap: "7px" }}>
              <span style={{ fontWeight: 800 }}>Ek Kurye</span>
              <input
                inputMode="numeric"
                value={extraHeadcountRequest}
                onChange={(event) => setExtraHeadcountRequest(event.target.value)}
                style={fieldStyle}
              />
            </label>
            <label style={{ display: "grid", gap: "7px" }}>
              <span style={{ fontWeight: 800 }}>Ek Talep Tarihi</span>
              <input
                type="date"
                value={extraHeadcountRequestDate}
                onChange={(event) => setExtraHeadcountRequestDate(event.target.value)}
                style={fieldStyle}
              />
            </label>
            <label style={{ display: "grid", gap: "7px" }}>
              <span style={{ fontWeight: 800 }}>Azaltma</span>
              <input
                inputMode="numeric"
                value={reduceHeadcountRequest}
                onChange={(event) => setReduceHeadcountRequest(event.target.value)}
                style={fieldStyle}
              />
            </label>
            <label style={{ display: "grid", gap: "7px" }}>
              <span style={{ fontWeight: 800 }}>Azaltma Tarihi</span>
              <input
                type="date"
                value={reduceHeadcountRequestDate}
                onChange={(event) => setReduceHeadcountRequestDate(event.target.value)}
                style={fieldStyle}
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={isPending || !selectedEntry}
            style={{
              width: "fit-content",
              padding: "12px 16px",
              borderRadius: "15px",
              border: "none",
              background: "linear-gradient(135deg, #0f7a72, #0f5fd7)",
              color: "#fff",
              fontWeight: 900,
              cursor: "pointer",
            }}
          >
            {isPending ? "Güncelleniyor..." : "Kadro Talebini Güncelle"}
          </button>
          {error ? <InlineMessage tone="error" message={error} /> : null}
          {success ? <InlineMessage tone="success" message={success} /> : null}
        </form>
      )}
    </section>
  );
}

function InlineMessage({ tone, message }: { tone: "error" | "success" | "soft"; message: string }) {
  const palette =
    tone === "error"
      ? { background: "rgba(205, 70, 66, 0.08)", border: "rgba(205, 70, 66, 0.18)", color: "#b53632" }
      : tone === "success"
        ? { background: "rgba(35, 148, 94, 0.08)", border: "rgba(35, 148, 94, 0.18)", color: "#1d7b4d" }
        : { background: "rgba(15, 95, 215, 0.06)", border: "rgba(15, 95, 215, 0.14)", color: "var(--muted)" };

  return (
    <div
      style={{
        padding: "12px 14px",
        borderRadius: "16px",
        border: `1px solid ${palette.border}`,
        background: palette.background,
        color: palette.color,
        fontWeight: 800,
      }}
    >
      {message}
    </div>
  );
}
