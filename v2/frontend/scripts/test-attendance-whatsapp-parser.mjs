import assert from "node:assert/strict";
import fs from "node:fs";
import { createRequire } from "node:module";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const parserSource = fs.readFileSync(
  new URL("../lib/attendance-whatsapp-parser.ts", import.meta.url),
  "utf8",
);
const transpiled = ts.transpileModule(parserSource, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2020,
  },
  reportDiagnostics: true,
});

assert.equal(transpiled.diagnostics?.length ?? 0, 0);

const moduleContext = { exports: {} };
vm.runInNewContext(transpiled.outputText, {
  module: moduleContext,
  exports: moduleContext.exports,
  require,
});

const {
  parseWhatsappAttendanceRows,
  parseWhatsappAttendanceDate,
  parseWhatsappWorkValues,
} = moduleContext.exports;

const people = [
  { id: 1, label: "Barış Özpamuk", role: "Kurye" },
  { id: 2, label: "Selehattin Çiftçi", role: "Kurye" },
  { id: 3, label: "Yusuf Demirci", role: "Kurye" },
  { id: 4, label: "Fatih Aslan", role: "Kurye" },
  { id: 5, label: "Musa Çoban", role: "Kurye" },
  { id: 6, label: "Güner Akdağ", role: "Kurye" },
  { id: 7, label: "Sude Eraslan", role: "Kurye" },
  { id: 8, label: "Hacı Altıkulaç", role: "Kurye" },
  { id: 9, label: "Evrem Karapınar", role: "Bölge Müdürü" },
];

assert.equal(parseWhatsappAttendanceDate("Rapor Kurye 20260416"), "2026-04-16");
const parenthesizedValues = parseWhatsappWorkValues("Sude Eraslan 8 (10 saat)");
assert.equal(parenthesizedValues.workedHours, 10);
assert.equal(parenthesizedValues.packageCount, 8);

const fasuli = parseWhatsappAttendanceRows(
  `[18.04.2026 11:01:18] Cihan Cat Kapinda: 17-04-2026
Beyoğlu Fasuli
Barış Özpamuk 18 paket 9 saat
Selehattin çiftçi 18 paket 9 saat
Vatan Fasuli
Yusuf Demirci 12 paket 9 saat`,
  people,
  "Fasuli - Beyoğlu",
);
assert.equal(fasuli.entryDate, "2026-04-17");
assert.equal(fasuli.rows.length, 2);
assert.equal(fasuli.rows[0].personId, 1);
assert.equal(fasuli.rows[0].packageCount, "18");
assert.equal(fasuli.rows[0].workedHours, "9");
assert.equal(fasuli.skippedByBranch, 1);

const sushico = parseWhatsappAttendanceRows(
  `17/04/2026
İdealistkent Sushico
Musa Çoban: 26 - 10 saat
Güner Akdağ:22 - 10 saat
Evrem Karapınar ::16 - 10 saat`,
  people,
  "Sushico - İdealistkent",
);
assert.equal(sushico.rows.length, 3);
assert.equal(sushico.rows[2].entryStatus, "Bölge Müdürü");
assert.equal(sushico.rows[2].packageCount, "16");
assert.equal(sushico.rows[2].workedHours, "10");

const quickChina = parseWhatsappAttendanceRows(
  `Quick China Suadiye
18/04/2026
Sude Eraslan  8 (10 saat)
Hacı altıkulaç  0 (2 saat)
Toplam Paket Sayısı = (26)`,
  people,
  "Quick China - Suadiye",
);
assert.equal(quickChina.entryDate, "2026-04-18");
assert.equal(quickChina.rows.length, 2);
assert.equal(quickChina.rows[0].personId, 7);
assert.equal(quickChina.rows[0].packageCount, "8");
assert.equal(quickChina.rows[0].workedHours, "10");
assert.equal(quickChina.rows[1].personId, 8);
assert.equal(quickChina.rows[1].packageCount, "0");
assert.equal(quickChina.rows[1].workedHours, "2");

const burger = parseWhatsappAttendanceRows(
  `Rapor Kurye 20260416
BURGER@ KAVACIK
Fatih Aslan (İzin)`,
  people,
  "Burger@ - Kavacık",
);
assert.equal(burger.entryDate, "2026-04-16");
assert.equal(burger.rows.length, 1);
assert.equal(burger.rows[0].personId, 4);
assert.equal(burger.rows[0].entryStatus, "İzin");
assert.equal(burger.rows[0].packageCount, "0");
assert.equal(burger.rows[0].workedHours, "0");

console.log("attendance WhatsApp parser tests passed");
