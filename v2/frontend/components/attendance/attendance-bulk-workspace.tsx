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
    fixed_monthly_fee: number;
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

function normalizeBulkStatus(value: string) {
  const normalized = String(value || "").trim().toLocaleLowerCase("tr-TR");
  const mapping: Record<string, string> = {
    normal: "Normal",
    joker: "Joker",
    izin: "İzin",
    raporlu: "Raporlu",
    "ihbarsız çıkış": "İhbarsız Çıkış",
    "ihbarsiz cikis": "İhbarsız Çıkış",
    gelmedi: "Gelmedi",
    "çıkış": "Çıkış yaptı",
    cikis: "Çıkış yaptı",
    "çıkış yaptı": "Çıkış yaptı",
    sef: "Şef",
    şef: "Şef",
  };
  return mapping[normalized] ?? "Normal";
}

function parseWhatsappRows(
  rawText: string,
  people: AttendanceFormOptions["people"],
): BulkRow[] {
  const personByFullName = new Map<string, AttendanceFormOptions["people"][number]>();
  const personByLabel = new Map<string, AttendanceFormOptions["people"][number]>();

  people.forEach((person) => {
    const label = person.label.trim();
    const fullName = label.split(" (")[0]?.trim() ?? label;
    personByLabel.set(label.toLocaleLowerCase("tr-TR"), person);
    personByFullName.set(fullName.toLocaleLowerCase("tr-TR"), person);
  });

  return rawText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const normalized = line.replaceAll("—", "-").replaceAll("–", "-");
      const parts = normalized
        .split(/\s*\|\s*|\s*;\s*|\s+-\s+/)
        .map((part) => part.trim())
        .filter(Boolean);
      if (!parts.length) {
        return null;
      }

      const nameToken = parts[0].toLocaleLowerCase("tr-TR");
      const matchedPerson = personByFullName.get(nameToken) ?? personByLabel.get(nameToken);
      let workedHours = 0;
      let packageCount = 0;
      let entryStatus = "Normal";
      let notes = "";

      parts.slice(1).forEach((part) => {
        const lower = part.toLocaleLowerCase("tr-TR");
        const numbers = lower.match(/\d+[.,]?\d*/g) ?? [];
        if (lower.includes("saat") && numbers[0]) {
          workedHours = Number(numbers[0].replace(",", "."));
          return;
        }
        if (lower.includes("paket") && numbers[0]) {
          packageCount = Number(numbers[0].replace(",", "."));
          return;
        }
        const normalizedStatus = normalizeBulkStatus(part);
        if (normalizedStatus !== "Normal" || lower === "normal") {
          entryStatus = normalizedStatus;
          return;
        }
        notes = notes ? `${notes} | ${part}` : part;
      });

      return {
        rowId: nextRowId(),
        personId: matchedPerson?.id ?? "",
        workedHours: String(workedHours),
        packageCount: String(packageCount),
        entryStatus,
        notes,
      } satisfies BulkRow;
    })
    .filter((row): row is BulkRow => row !== null);
}

export function AttendanceBulkWorkspace() {
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
        throw new Error("Toplu puantaj seçenekleri yüklenemedi.");
      }
      const payload = (await response.json()) as AttendanceFormOptions;
      setOptions(payload);
      setRestaurantId(payload.selected_restaurant_id ?? "");
      setRows(buildRowsFromPeople(payload.people));
    } catch (error) {
      setSubmitError(
        error instanceof Error ? error.message : "Toplu puantaj seçenekleri yüklenemedi.",
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
    const parsedRows = parseWhatsappRows(rawText, people);
    if (!parsedRows.length) {
      setSubmitError("Metinden tabloya aktarılacak okunabilir bir satır bulunamadı.");
      return;
    }
    setRows(parsedRows);
    setSubmitSuccess(`${parsedRows.length} satır tabloya aktarıldı.`);
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
              placeholder="Örnek: Ali Yılmaz - 10 saat - 38 paket - Normal"
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
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(220px, 2fr) repeat(3, minmax(110px, 0.8fr)) minmax(220px, 1.6fr) 72px",
                gap: "10px",
                padding: "0 8px",
                color: "var(--muted)",
                fontSize: "0.75rem",
                fontWeight: 800,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
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
