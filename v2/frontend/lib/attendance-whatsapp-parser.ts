export type AttendanceWhatsappPerson = {
  id: number;
  label: string;
  role: string;
};

export type ParsedAttendanceWhatsappRow = {
  personId: number | "";
  workedHours: string;
  packageCount: string;
  entryStatus: string;
  notes: string;
};

export type AttendanceWhatsappParseResult = {
  entryDate: string | null;
  rows: ParsedAttendanceWhatsappRow[];
  unmatchedCount: number;
  skippedByBranch: number;
};

export function normalizeAttendanceLookupText(value: string) {
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

function buildDate(year: string, month: string, day: string) {
  const numericMonth = Number(month);
  const numericDay = Number(day);
  if (
    !Number.isInteger(numericMonth) ||
    !Number.isInteger(numericDay) ||
    numericMonth < 1 ||
    numericMonth > 12 ||
    numericDay < 1 ||
    numericDay > 31
  ) {
    return null;
  }
  return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
}

export function parseWhatsappAttendanceDate(line: string) {
  const datedMatches = Array.from(line.matchAll(/\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b/g));
  if (datedMatches.length) {
    const match = datedMatches[datedMatches.length - 1];
    const [, day, month, year] = match;
    return buildDate(year, month, day);
  }

  const compactMatches = Array.from(line.matchAll(/\b(20\d{2})(\d{2})(\d{2})\b/g));
  if (compactMatches.length) {
    const match = compactMatches[compactMatches.length - 1];
    const [, year, month, day] = match;
    return buildDate(year, month, day);
  }

  return null;
}

function parseDecimalToken(value: string | undefined) {
  if (!value) {
    return 0;
  }
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizedIncludes(normalized: string, term: string) {
  const normalizedTerm = normalizeAttendanceLookupText(term);
  return ` ${normalized} `.includes(` ${normalizedTerm} `);
}

function inferStatusFromLine(line: string, person: AttendanceWhatsappPerson | undefined) {
  const normalized = normalizeAttendanceLookupText(line);
  if (normalizedIncludes(normalized, "bolge muduru")) {
    return "Bölge Müdürü";
  }
  if (normalizedIncludes(normalized, "joker")) {
    return "Joker";
  }
  if (normalizedIncludes(normalized, "sef")) {
    return "Şef";
  }
  if (normalizedIncludes(normalized, "ihbarsiz cikis")) {
    return "İhbarsız Çıkış";
  }
  if (normalizedIncludes(normalized, "cikis")) {
    return "Çıkış yaptı";
  }
  if (normalizedIncludes(normalized, "raporlu") || normalizedIncludes(normalized, "rapor")) {
    return "Raporlu";
  }
  if (normalizedIncludes(normalized, "gelmedi")) {
    return "Gelmedi";
  }
  if (normalizedIncludes(normalized, "izin")) {
    return "İzin";
  }

  const role = normalizeAttendanceLookupText(person?.role ?? "");
  if (normalizedIncludes(role, "bolge muduru")) {
    return "Bölge Müdürü";
  }
  if (normalizedIncludes(role, "joker")) {
    return "Joker";
  }
  if (normalizedIncludes(role, "sef")) {
    return "Şef";
  }
  return "Normal";
}

export function parseWhatsappWorkValues(line: string) {
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
    .replace(/\b20\d{6}\b/g, " ")
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

function shouldSkipMetaLine(line: string) {
  const normalizedLine = normalizeAttendanceLookupText(line);
  if (
    normalizedLine.includes("toplam paket") ||
    normalizedLine.includes("toplam paket sayisi") ||
    normalizedLine.includes("devamini okuyun") ||
    normalizedLine.includes("rapor kurye")
  ) {
    return true;
  }

  const weekdayNames = [
    "pazartesi",
    "sali",
    "carsamba",
    "persembe",
    "cuma",
    "cumartesi",
    "pazar",
  ];
  if (weekdayNames.some((weekday) => normalizedLine.endsWith(weekday))) {
    return true;
  }

  return /^\[?\d{1,2}[./-]\d{1,2}[./-]\d{4}/.test(line);
}

export function parseWhatsappAttendanceRows(
  rawText: string,
  people: AttendanceWhatsappPerson[],
  selectedRestaurantLabel?: string,
): AttendanceWhatsappParseResult {
  const personCandidates = people
    .map((person) => {
      const label = person.label.trim();
      const fullName = label.split(" (")[0]?.trim() ?? label;
      const lookupKey = normalizeAttendanceLookupText(fullName);
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
  const selectedRestaurantKey = normalizeAttendanceLookupText(selectedRestaurantLabel ?? "");
  const rows = rawText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const lineDate = parseWhatsappAttendanceDate(line);
      if (lineDate) {
        detectedDate = detectedDate ?? lineDate;
      }

      const normalizedLine = normalizeAttendanceLookupText(line);
      if (shouldSkipMetaLine(line)) {
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
      const { workedHours, packageCount } = parseWhatsappWorkValues(line);
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
        personId: matchedPerson?.id ?? "",
        workedHours: String(workedHours || 0),
        packageCount: String(packageCount || 0),
        entryStatus,
        notes: matchedPerson ? "" : `Eşleşmeyen WhatsApp satırı: ${line}`,
      } satisfies ParsedAttendanceWhatsappRow;
    })
    .filter((row): row is ParsedAttendanceWhatsappRow => row !== null);

  return { entryDate: detectedDate, rows, unmatchedCount, skippedByBranch };
}
