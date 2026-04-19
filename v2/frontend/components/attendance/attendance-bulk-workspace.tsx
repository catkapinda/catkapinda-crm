"use client";

import type { CSSProperties } from "react";
import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "../../lib/api";

type AttendanceFormOptions = {
  restaurants: Array<{
    id: number;
    label: string;
    pricing_model: string;
    pricing_model_label: string;
    hourly_rate: number;
    package_rate: number;
    package_threshold: number;
    package_rate_low: number;
    package_rate_high: number;
    fixed_monthly_fee: number;
    vat_rate: number;
  }>;
  people: Array<{
    id: number;
    label: string;
    role: string;
  }>;
  bulk_statuses: string[];
  selected_restaurant_id: number | null;
};

type BulkRow = {
  rowId: number;
  personId: number | "";
  workedHours: string;
  packageCount: string;
  entryStatus: string;
  notes: string;
};

type AttendanceBulkWorkspaceProps = {
  onDataChange?: () => void;
};

function buildRowCounter(start = 1) {
  let current = start;
  return () => {
    const nextValue = current;
    current += 1;
    return nextValue;
  };
}

const nextRowId = buildRowCounter();

function buildRowsFromPeople(people: AttendanceFormOptions["people"]): BulkRow[] {
  return people.map((person) => ({
    rowId: nextRowId(),
    personId: person.id,
    workedHours: "0",
    packageCount: "0",
    entryStatus: "Normal",
    notes: "",
  }));
}

function buildEmptyRow(): BulkRow {
  return {
    rowId: nextRowId(),
    personId: "",
    workedHours: "0",
    packageCount: "0",
    entryStatus: "Normal",
    notes: "",
  };
}

function normalizeLookupText(value: string) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replaceAll("ı", "i")
    .replaceAll("İ", "I")
    .toLocaleLowerCase("tr-TR")
    .replaceAll("ı", "i")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function collapseRepeatedLetters(value: string) {
  return value.replace(/([a-z])\1+/g, "$1");
}

function parseWhatsappDate(line: string) {
  const matches = Array.from(line.matchAll(/\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b/g));
  if (!matches.length) {
    return null;
  }
  const match = matches[matches.length - 1];
  const [, day, month, year] = match;
  return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
}

function parseDecimalToken(value: string | undefined) {
  if (!value) {
    return 0;
  }
  return Number(value.replace(",", "."));
}

function toNumber(value: string | number) {
  const parsed = Number(String(value || "0").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatCurrency(value: number) {
  return `${Number(value || 0).toLocaleString("tr-TR", {
    maximumFractionDigits: 0,
  })} TL`;
}

function calculateRowInvoice(
  restaurant: AttendanceFormOptions["restaurants"][number] | null,
  row: BulkRow,
) {
  if (!restaurant || row.entryStatus !== "Normal") {
    return 0;
  }
  const workedHours = toNumber(row.workedHours);
  const packageCount = toNumber(row.packageCount);
  if (restaurant.pricing_model === "hourly_plus_package") {
    return workedHours * restaurant.hourly_rate + packageCount * restaurant.package_rate;
  }
  if (restaurant.pricing_model === "threshold_package") {
    const packageRate =
      packageCount <= restaurant.package_threshold
        ? restaurant.package_rate_low
        : restaurant.package_rate_high;
    return workedHours * restaurant.hourly_rate + packageCount * packageRate;
  }
  if (restaurant.pricing_model === "hourly_only") {
    return workedHours * restaurant.hourly_rate;
  }
  if (restaurant.pricing_model === "fixed_monthly") {
    return workedHours > 0 || packageCount > 0 ? restaurant.fixed_monthly_fee : 0;
  }
  return 0;
}

function inferStatusFromLine(
  line: string,
  person: AttendanceFormOptions["people"][number] | undefined,
) {
  const normalized = normalizeLookupText(line);
  if (normalized.includes("bolge muduru")) {
    return "Bölge Müdürü";
  }
  if (normalized.includes("joker")) {
    return "Joker";
  }
  if (normalized.includes("sef")) {
    return "Şef";
  }
  if (normalized.includes("ihbarsiz cikis")) {
    return "İhbarsız Çıkış";
  }
  if (normalized.includes("cikis")) {
    return "Çıkış yaptı";
  }
  if (normalized.includes("raporlu")) {
    return "Raporlu";
  }
  if (normalized.includes("gelmedi")) {
    return "Gelmedi";
  }
  if (normalized.includes("izin")) {
    return "İzin";
  }

  const role = normalizeLookupText(person?.role ?? "");
  if (role.includes("bolge muduru")) {
    return "Bölge Müdürü";
  }
  if (role.includes("joker")) {
    return "Joker";
  }
  if (role.includes("sef")) {
    return "Şef";
  }
  return "Normal";
}

function parseWorkValues(line: string) {
  const normalizedLine = line.replaceAll("—", "-").replaceAll("–", "-");
  const hourMatch = normalizedLine.match(/(\d+[.,]?\d*)\s*(?:saat|sa)\b/i);
  const packageMatch = normalizedLine.match(/(\d+[.,]?\d*)\s*(?:paket|pkg)\b/i);
  const workedHours = parseDecimalToken(hourMatch?.[1]);

  if (packageMatch?.[1]) {
    return {
      workedHours,
      packageCount: parseDecimalToken(packageMatch[1]),
    };
  }

  const scrubbed = normalizedLine
    .replace(/\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b/g, " ")
    .replace(/(\d+[.,]?\d*)\s*(?:saat|sa)\b/gi, " ")
    .replace(/\([^)]*(?:saat|sa)[^)]*\)/gi, " ");
  const numbers = scrubbed.match(/\d+[.,]?\d*/g) ?? [];

  return {
    workedHours,
    packageCount: parseDecimalToken(numbers[0]),
  };
}

function restaurantHeadingMatches(lineKey: string, selectedRestaurantKey: string) {
  if (!lineKey || !selectedRestaurantKey) {
    return false;
  }
  const lineTokens = new Set(lineKey.split(" ").filter(Boolean));
  const selectedTokens = selectedRestaurantKey.split(" ").filter(Boolean);
  const selectedTokenSet = new Set(selectedTokens);
  const overlapCount = Array.from(lineTokens).filter((token) => selectedTokenSet.has(token)).length;
  return (
    selectedTokens.length > 0 &&
    (selectedTokens.every((token) => lineTokens.has(token)) ||
      Array.from(lineTokens).every((token) => selectedTokenSet.has(token)) ||
      overlapCount >= Math.min(2, selectedTokens.length))
  );
}

function looksLikeRestaurantHeading(lineKey: string) {
  const tokens = lineKey.split(" ").filter(Boolean);
  return tokens.length >= 2;
}

function parseWhatsappRows(
  rawText: string,
  people: AttendanceFormOptions["people"],
  selectedRestaurantLabel?: string,
): { entryDate: string | null; rows: BulkRow[]; unmatchedCount: number; skippedByBranch: number } {
  const personCandidates = people
    .map((person) => {
      const label = person.label.trim();
      const fullName = label.split(" (")[0]?.trim() ?? label;
      const lookupKey = normalizeLookupText(fullName);
      return {
        person,
        lookupKey,
        collapsedLookupKey: collapseRepeatedLetters(lookupKey),
      };
    })
    .filter((item) => item.lookupKey)
    .sort((left, right) => right.lookupKey.length - left.lookupKey.length);

  let detectedDate: string | null = null;
  let unmatchedCount = 0;
  let skippedByBranch = 0;
  let sawRestaurantHeading = false;
  let insideSelectedRestaurant = true;
  const selectedRestaurantKey = normalizeLookupText(selectedRestaurantLabel ?? "");
  const rows = rawText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const lineDate = parseWhatsappDate(line);
      if (lineDate) {
        detectedDate = detectedDate ?? lineDate;
      }

      const normalizedLine = normalizeLookupText(line);
      if (
        normalizedLine.includes("toplam paket") ||
        normalizedLine.includes("devamini okuyun") ||
        /^\[?\d{1,2}[./-]\d{1,2}[./-]\d{4}/.test(line) ||
        normalizedLine.endsWith("cumartesi") ||
        normalizedLine.endsWith("pazar")
      ) {
        return null;
      }

      const collapsedLine = collapseRepeatedLetters(normalizedLine);
      const matchedPerson = personCandidates.find(
        (candidate) =>
          normalizedLine === candidate.lookupKey ||
          normalizedLine.startsWith(`${candidate.lookupKey} `) ||
          collapsedLine === candidate.collapsedLookupKey ||
          collapsedLine.startsWith(`${candidate.collapsedLookupKey} `),
      )?.person;
      const { workedHours, packageCount } = parseWorkValues(line);
      const entryStatus = inferStatusFromLine(line, matchedPerson);

      if (!matchedPerson && !workedHours && !packageCount && entryStatus === "Normal") {
        if (selectedRestaurantKey && looksLikeRestaurantHeading(normalizedLine)) {
          sawRestaurantHeading = true;
          insideSelectedRestaurant = restaurantHeadingMatches(
            normalizedLine,
            selectedRestaurantKey,
          );
        }
        return null;
      }

      if (sawRestaurantHeading && !insideSelectedRestaurant) {
        skippedByBranch += 1;
        return null;
      }

      if (!matchedPerson) {
        if (!workedHours && !packageCount && entryStatus === "Normal") {
          return null;
        }
        unmatchedCount += 1;
      }

      return {
        rowId: nextRowId(),
        personId: matchedPerson?.id ?? "",
        workedHours: String(workedHours || 0),
        packageCount: String(packageCount || 0),
        entryStatus,
        notes: matchedPerson ? "" : `Eşleşmeyen WhatsApp satırı: ${line}`,
      } satisfies BulkRow;
    })
    .filter((row): row is BulkRow => row !== null);

  return { entryDate: detectedDate, rows, unmatchedCount, skippedByBranch };
}

export function AttendanceBulkWorkspace({ onDataChange }: AttendanceBulkWorkspaceProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [options, setOptions] = useState<AttendanceFormOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [entryDate, setEntryDate] = useState(new Date().toISOString().slice(0, 10));
  const [restaurantId, setRestaurantId] = useState<number | "">("");
  const [includeAllActive, setIncludeAllActive] = useState(true);
  const [rows, setRows] = useState<BulkRow[]>([]);
  const [rawText, setRawText] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [submitSuccess, setSubmitSuccess] = useState("");
  const didInitialLoad = useRef(false);

  async function loadOptions(nextRestaurantId?: number | "", nextIncludeAllActive?: boolean) {
    setLoadingOptions(true);
    try {
      const params = new URLSearchParams();
      const resolvedRestaurantId =
        typeof nextRestaurantId === "number" ? nextRestaurantId : undefined;
      const resolvedIncludeAllActive = nextIncludeAllActive ?? includeAllActive;
      if (typeof resolvedRestaurantId === "number") {
        params.set("restaurant_id", String(resolvedRestaurantId));
      }
      params.set("include_all_active", resolvedIncludeAllActive ? "true" : "false");
      const query = params.size ? `?${params.toString()}` : "";
      const response = await apiFetch(`/attendance/form-options${query}`);
      if (!response.ok) {
        throw new Error("Toplu puantaj seçenekleri alınamadı. Lütfen tekrar dene.");
      }
      const payload = (await response.json()) as AttendanceFormOptions;
      setOptions(payload);
      setRestaurantId(payload.selected_restaurant_id ?? "");
      setRows(buildRowsFromPeople(payload.people));
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Toplu puantaj seçenekleri alınamadı. Lütfen tekrar dene.",
      );
    } finally {
      setLoadingOptions(false);
    }
  }

  useEffect(() => {
    if (didInitialLoad.current) {
      return;
    }
    didInitialLoad.current = true;
    void loadOptions();
  }, []);

  const people = options?.people ?? [];
  const bulkStatuses = options?.bulk_statuses ?? ["Normal"];
  const personOptions = useMemo(
    () => new Map(people.map((person) => [person.id, person.label])),
    [people],
  );
  const selectedRestaurant = useMemo(() => {
    if (!options || typeof restaurantId !== "number") {
      return null;
    }
    return options.restaurants.find((restaurant) => restaurant.id === restaurantId) ?? null;
  }, [options, restaurantId]);
  const financePreview = useMemo(() => {
    const activeRows = rows.filter((row) => typeof row.personId === "number");
    const totalHours = activeRows.reduce((sum, row) => sum + toNumber(row.workedHours), 0);
    const totalPackages = activeRows.reduce((sum, row) => sum + toNumber(row.packageCount), 0);
    const netInvoice =
      selectedRestaurant?.pricing_model === "fixed_monthly"
        ? activeRows.some((row) => row.entryStatus === "Normal" && (toNumber(row.workedHours) > 0 || toNumber(row.packageCount) > 0))
          ? selectedRestaurant.fixed_monthly_fee
          : 0
        : activeRows.reduce((sum, row) => sum + calculateRowInvoice(selectedRestaurant, row), 0);
    const vatRate = selectedRestaurant?.vat_rate ?? 20;
    return {
      activeCount: activeRows.length,
      totalHours,
      totalPackages,
      netInvoice,
      grossInvoice: netInvoice * (1 + vatRate / 100),
    };
  }, [rows, selectedRestaurant]);

  function updateRow(rowId: number, patch: Partial<BulkRow>) {
    setRows((currentRows) =>
      currentRows.map((row) => (row.rowId === rowId ? { ...row, ...patch } : row)),
    );
  }

  async function handleRestaurantChange(nextValue: string) {
    const nextRestaurantId = Number(nextValue);
    setRestaurantId(nextRestaurantId);
    setSubmitError("");
    setSubmitSuccess("");
    await loadOptions(nextRestaurantId, includeAllActive);
  }

  async function handleIncludeAllActiveChange(checked: boolean) {
    setIncludeAllActive(checked);
    setSubmitError("");
    setSubmitSuccess("");
    await loadOptions(
      typeof restaurantId === "number" ? restaurantId : undefined,
      checked,
    );
  }

  function handleParseText() {
    setSubmitError("");
    setSubmitSuccess("");
    const selectedRestaurantLabel =
      options?.restaurants.find((restaurant) => restaurant.id === restaurantId)?.label ?? "";
    const parsedResult = parseWhatsappRows(rawText, people, selectedRestaurantLabel);
    const parsedRows = parsedResult.rows;
    if (!parsedRows.length) {
      setSubmitError("Metinden tabloya aktarılacak okunabilir bir satır bulunamadı.");
      return;
    }
    if (parsedResult.entryDate) {
      setEntryDate(parsedResult.entryDate);
    }
    setRows(parsedRows);
    setSubmitSuccess(
      `${parsedRows.length} satır tabloya aktarıldı.${
        parsedResult.entryDate ? ` Tarih ${parsedResult.entryDate} olarak alındı.` : ""
      }${
        parsedResult.unmatchedCount
          ? ` ${parsedResult.unmatchedCount} satırda personel eşleşmedi; kaydetmeden önce seç.`
          : ""
      }${
        parsedResult.skippedByBranch
          ? ` ${parsedResult.skippedByBranch} satır farklı şube başlığı altında olduğu için alınmadı.`
          : ""
      }`,
    );
  }

  async function handleSubmit() {
    setSubmitError("");
    setSubmitSuccess("");

    if (typeof restaurantId !== "number") {
      setSubmitError("Toplu puantaj için önce bir şube seçmelisin.");
      return;
    }

    const response = await apiFetch("/attendance/entries/bulk", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        entry_date: entryDate,
        restaurant_id: restaurantId,
        include_all_active: includeAllActive,
        rows: rows.map((row) => ({
          person_id: typeof row.personId === "number" ? row.personId : null,
          worked_hours: Number(row.workedHours || 0),
          package_count: Number(row.packageCount || 0),
          entry_status: row.entryStatus,
          notes: row.notes,
        })),
      }),
    });

    const payload = (await response.json().catch(() => null)) as
      | { detail?: string; message?: string }
      | null;

    if (!response.ok) {
      setSubmitError(payload?.detail || "Toplu puantaj kaydı oluşturulamadı.");
      return;
    }

    setSubmitSuccess(payload?.message || "Toplu puantaj kaydı oluşturuldu.");
    onDataChange?.();
    setRawText("");
    setRows(buildRowsFromPeople(people));
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
        <h2 style={{ margin: 0, fontSize: "1.2rem" }}>Toplu Puantaj</h2>
        <p
          style={{
            margin: "6px 0 0",
            color: "var(--muted)",
            lineHeight: 1.7,
          }}
        >
          Bir şubedeki birden fazla kurye için saat, paket ve durumu tek masada gir. İstersen
          WhatsApp metnini yapıştırıp tabloyu hızlıca doldur.
        </p>
      </div>

      {loadingOptions ? (
        <div style={infoCardStyle}>Toplu puantaj seçenekleri yükleniyor...</div>
      ) : (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "14px",
            }}
          >
            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Tarih</span>
              <input
                type="date"
                value={entryDate}
                onChange={(event) => setEntryDate(event.target.value)}
                style={fieldStyle}
              />
            </label>

            <label style={{ display: "grid", gap: "8px" }}>
              <span style={{ fontWeight: 700 }}>Şube</span>
              <select
                value={restaurantId}
                onChange={(event) => {
                  void handleRestaurantChange(event.target.value);
                }}
                style={fieldStyle}
              >
                {options?.restaurants.map((restaurant) => (
                  <option key={restaurant.id} value={restaurant.id}>
                    {restaurant.label}
                  </option>
                ))}
              </select>
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "end",
                gap: "10px",
                padding: "0 4px 12px",
                fontWeight: 700,
              }}
            >
              <input
                type="checkbox"
                checked={includeAllActive}
                onChange={(event) => {
                  void handleIncludeAllActiveChange(event.target.checked);
                }}
              />
              Tüm aktif personeli göster
            </label>
          </div>

          {selectedRestaurant ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
                gap: "10px",
                padding: "14px",
                borderRadius: "18px",
                background: "rgba(17, 125, 87, 0.08)",
                border: "1px solid rgba(17, 125, 87, 0.12)",
              }}
            >
              {[
                ["Şube", selectedRestaurant.label],
                ["Model", selectedRestaurant.pricing_model_label],
                ["Personel", String(financePreview.activeCount)],
                ["Saat", financePreview.totalHours.toLocaleString("tr-TR", { maximumFractionDigits: 1 })],
                ["Paket", financePreview.totalPackages.toLocaleString("tr-TR", { maximumFractionDigits: 0 })],
                ["Tahmini Fatura", formatCurrency(financePreview.grossInvoice)],
              ].map(([label, value]) => (
                <div key={label} style={{ display: "grid", gap: "3px" }}>
                  <span
                    style={{
                      color: "var(--muted)",
                      fontSize: "0.72rem",
                      fontWeight: 900,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    {label}
                  </span>
                  <strong style={{ color: "var(--text)", fontSize: "0.95rem" }}>{value}</strong>
                </div>
              ))}
            </div>
          ) : null}

          <div
            style={{
              display: "grid",
              gap: "10px",
              padding: "18px",
              borderRadius: "18px",
              background: "rgba(15, 95, 215, 0.06)",
              border: "1px solid rgba(15, 95, 215, 0.08)",
            }}
          >
            <div style={{ fontWeight: 800 }}>WhatsApp metninden tablo oluştur</div>
            <textarea
              value={rawText}
              onChange={(event) => setRawText(event.target.value)}
              rows={4}
              placeholder={`Örnek:
18.04.2026
BURGER@ KAVACIK
Fatih Aslan (İzin)
Ali Yılmaz 18 paket 9 saat
Musa Çoban: 26 - 10 saat`}
              style={{ ...fieldStyle, resize: "vertical", minHeight: "110px" }}
            />
            <div
              style={{
                display: "flex",
                gap: "10px",
                flexWrap: "wrap",
              }}
            >
              <button type="button" onClick={handleParseText} style={secondaryButtonStyle}>
                Metni tabloya aktar
              </button>
              <button
                type="button"
                onClick={() => setRows(buildRowsFromPeople(people))}
                style={ghostButtonStyle}
              >
                Listeyi sıfırla
              </button>
              <button
                type="button"
                onClick={() => setRows((currentRows) => [...currentRows, buildEmptyRow()])}
                style={ghostButtonStyle}
              >
                Boş satır ekle
              </button>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gap: "10px",
              maxHeight: "520px",
              overflow: "auto",
              paddingRight: "2px",
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(220px, 2fr) repeat(3, minmax(110px, 0.8fr)) minmax(220px, 1.6fr) 72px",
                gap: "10px",
                padding: "8px",
                color: "var(--muted)",
                fontSize: "0.75rem",
                fontWeight: 800,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                position: "sticky",
                top: 0,
                zIndex: 1,
                borderRadius: "14px",
                background: "var(--surface-strong)",
              }}
            >
              <span>Personel</span>
              <span>Saat</span>
              <span>Paket</span>
              <span>Durum</span>
              <span>Not</span>
              <span>Sil</span>
            </div>

            {rows.map((row) => (
              <div
                key={row.rowId}
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "minmax(220px, 2fr) repeat(3, minmax(110px, 0.8fr)) minmax(220px, 1.6fr) 72px",
                  gap: "10px",
                  alignItems: "center",
                }}
              >
                <select
                  value={row.personId}
                  onChange={(event) =>
                    updateRow(row.rowId, { personId: Number(event.target.value) || "" })
                  }
                  style={fieldStyle}
                >
                  <option value="">Personel seç</option>
                  {people.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.label}
                    </option>
                  ))}
                </select>

                <input
                  type="number"
                  min="0"
                  step="0.5"
                  value={row.workedHours}
                  onChange={(event) => updateRow(row.rowId, { workedHours: event.target.value })}
                  style={fieldStyle}
                />

                <input
                  type="number"
                  min="0"
                  step="1"
                  value={row.packageCount}
                  onChange={(event) => updateRow(row.rowId, { packageCount: event.target.value })}
                  style={fieldStyle}
                />

                <select
                  value={row.entryStatus}
                  onChange={(event) => updateRow(row.rowId, { entryStatus: event.target.value })}
                  style={fieldStyle}
                >
                  {bulkStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>

                <input
                  type="text"
                  value={row.notes}
                  onChange={(event) => updateRow(row.rowId, { notes: event.target.value })}
                  style={fieldStyle}
                  placeholder={
                    typeof row.personId === "number"
                      ? `${personOptions.get(row.personId) ?? "Personel"} için not`
                      : "İsteğe bağlı not"
                  }
                />

                <button
                  type="button"
                  onClick={() =>
                    setRows((currentRows) =>
                      currentRows.length <= 1
                        ? [buildEmptyRow()]
                        : currentRows.filter((item) => item.rowId !== row.rowId),
                    )
                  }
                  style={removeButtonStyle}
                >
                  Sil
                </button>
              </div>
            ))}
          </div>

          {submitError ? <div style={errorCardStyle}>{submitError}</div> : null}
          {submitSuccess ? <div style={successCardStyle}>{submitSuccess}</div> : null}

          <button
            type="button"
            onClick={() => {
              void handleSubmit();
            }}
            disabled={isPending || loadingOptions}
            style={{
              border: 0,
              borderRadius: "18px",
              padding: "15px 18px",
              fontWeight: 900,
              fontSize: "1rem",
              background: "var(--accent)",
              color: "#fff",
              cursor: "pointer",
              opacity: isPending ? 0.72 : 1,
            }}
          >
            {isPending ? "Toplu kayıt yenileniyor..." : "Tümünü Kaydet"}
          </button>
        </>
      )}
    </section>
  );
}

const fieldStyle: CSSProperties = {
  borderRadius: "16px",
  border: "1px solid var(--line)",
  background: "rgba(255, 255, 255, 0.9)",
  color: "var(--text)",
  padding: "12px 14px",
  font: "inherit",
};

const infoCardStyle: CSSProperties = {
  padding: "18px",
  borderRadius: "18px",
  background: "rgba(15, 95, 215, 0.06)",
  color: "var(--muted)",
};

const errorCardStyle: CSSProperties = {
  padding: "14px 16px",
  borderRadius: "16px",
  background: "rgba(196, 53, 53, 0.08)",
  color: "#9e2430",
};

const successCardStyle: CSSProperties = {
  padding: "14px 16px",
  borderRadius: "16px",
  background: "rgba(17, 125, 87, 0.10)",
  color: "#0c6b4b",
};

const secondaryButtonStyle: CSSProperties = {
  borderRadius: "14px",
  border: 0,
  padding: "11px 14px",
  background: "var(--accent)",
  color: "#fff",
  fontWeight: 800,
  cursor: "pointer",
};

const ghostButtonStyle: CSSProperties = {
  borderRadius: "14px",
  border: "1px solid var(--line)",
  padding: "11px 14px",
  background: "rgba(255,255,255,0.75)",
  color: "var(--text)",
  fontWeight: 700,
  cursor: "pointer",
};

const removeButtonStyle: CSSProperties = {
  borderRadius: "14px",
  border: "1px solid rgba(196, 53, 53, 0.18)",
  padding: "11px 10px",
  background: "rgba(196, 53, 53, 0.08)",
  color: "#9e2430",
  fontWeight: 800,
  cursor: "pointer",
};
