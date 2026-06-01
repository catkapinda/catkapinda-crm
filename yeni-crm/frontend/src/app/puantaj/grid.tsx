'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowDownToLine, ArrowUpFromLine, BarChart3, Check, Copy, Loader2,
  Send, ShieldCheck, AlertCircle,
} from 'lucide-react';

import {
  type MatrixCell,
  type MatrixRow,
  type PuantajMatrix,
  type PuantajApproval,
  type ReplacementCandidatesResponse,
  bulkFillPuantaj,
  getReplacementCandidates,
  submitPuantajApproval,
  updatePuantajCell,
} from '@/lib/api';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

const TR_DAYS = ['Paz', 'Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cts'];

function formatPeriod(p: string): string {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function tr(value: number, digits = 0): string {
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function avatarClass(role: string | null): string {
  if (role === 'Joker') return 'av-cream';
  if (role === 'Bölge Müdürü') return 'av-navy';
  if (role === 'Kaptan' || role === 'Restoran Takım Şefi') return 'av-cream';
  return 'av-blue';
}

const AV_COLORS: Record<string, string> = {
  'av-blue': 'bg-gradient-to-br from-blue-700 to-blue-500 text-white',
  'av-navy': 'bg-gradient-to-br from-blue-900 to-blue-700 text-white',
  'av-cream': 'bg-gradient-to-br from-yellow-600 to-yellow-400 text-white',
  'av-slate': 'bg-gradient-to-br from-slate-700 to-slate-500 text-white',
};

// Ayın gün sayısı
function daysInMonth(period: string): number {
  const [y, m] = period.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return 31;
  return new Date(y, m, 0).getDate();
}

// Haftanın günü (0 Pazar)
function dayOfWeek(period: string, day: number): number {
  const [y, m] = period.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return 0;
  return new Date(y, m - 1, day).getDay();
}

// Bugün mü?
function isToday(period: string, day: number): boolean {
  const today = new Date();
  const [y, m] = period.split('-').map((s) => parseInt(s, 10));
  return (
    today.getFullYear() === y &&
    today.getMonth() + 1 === m &&
    today.getDate() === day
  );
}

export function PuantajGrid({
  matrix: initialMatrix, period, periods,
}: {
  matrix: PuantajMatrix;
  period: string;
  periods: string[];
}) {
  // Lokal matrix state — optimistic UI için (sayfa yenilemeye gerek kalmasın)
  const [matrix, setMatrix] = useState<PuantajMatrix>(initialMatrix);
  // Period veya initial matrix değişirse senkronize et
  useEffect(() => {
    setMatrix(initialMatrix);
  }, [initialMatrix]);

  const [search, setSearch] = useState('');
  const [restFilter, setRestFilter] = useState<string | null>(null);
  const [roleFilter, setRoleFilter] = useState<string | null>(null);
  const [hideSupport, setHideSupport] = useState(false);
  const [editing, setEditing] = useState<{
    row: MatrixRow;
    day: number;
    cell: MatrixCell;
    pos: { x: number; y: number };
  } | null>(null);

  // Hücre güncelleme — popover save callback'i (optimistic)
  const updateLocalCell = (rowId: number, rowKey: string, day: number, newCell: MatrixCell) => {
    setMatrix((prev) => ({
      ...prev,
      rows: prev.rows.map((r) => {
        if (r.row_key !== rowKey) return r;
        const newCells = r.cells.map((c, i) => (i === day - 1 ? newCell : c));
        // Toplam yeniden hesapla (sadece normal hücreler)
        let totalHours = 0;
        let totalPkts = 0;
        let workedDays = 0;
        for (const c of newCells) {
          if (c.type === 'normal') {
            totalHours += c.hours || 0;
            totalPkts += c.packages || 0;
            workedDays += 1;
          }
        }
        return {
          ...r,
          cells: newCells,
          total_hours: totalHours,
          total_packages: totalPkts,
          worked_days: workedDays,
        };
      }),
    }));
  };
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkMsg, setBulkMsg] = useState<string | null>(null);
  const [submitBusy, setSubmitBusy] = useState(false);
  const [submitMsg, setSubmitMsg] = useState<string | null>(null);
  const router = useRouter();

  const totalDays = daysInMonth(period);

  async function runBulk(
    pattern: 'weekdays' | 'all' | 'weekend_off' | 'copy_previous',
    hours = 9,
    scoped: 'all' | 'view' = 'all',
  ) {
    if (bulkBusy) return;
    const label =
      pattern === 'copy_previous'
        ? 'Geçen aydan kopyala'
        : pattern === 'weekend_off'
        ? 'Hafta sonu boş + hafta içi 9 saat'
        : pattern === 'weekdays'
        ? 'Hafta içi → 9 saat'
        : 'Tüm gün → 9 saat';
    const personnel_ids = scoped === 'view'
      ? Array.from(new Set(filtered.filter((r) => !r.is_support_row).map((r) => r.id)))
      : undefined;
    const scopeLabel = scoped === 'view'
      ? `görünümdeki ${personnel_ids?.length ?? 0} kişi`
      : 'tüm aktif kuryeler';
    if (!confirm(`${label} (${scopeLabel}) işlemini onayla?\nMevcut hücreler atlanır, sadece boşlar doldurulur.`)) return;
    if (personnel_ids && personnel_ids.length === 0) {
      setBulkMsg('Görünümde uygun kişi yok');
      setTimeout(() => setBulkMsg(null), 4000);
      return;
    }
    setBulkBusy(true);
    setBulkMsg(null);
    try {
      const res = await bulkFillPuantaj({ period, pattern, hours, personnel_ids });
      setBulkMsg(`${res.inserted} kayıt eklendi · ${res.skipped} atlandı (zaten dolu)`);
      router.refresh();
    } catch (err) {
      setBulkMsg(
        err instanceof Error ? err.message : 'Hata oluştu',
      );
    } finally {
      setBulkBusy(false);
      setTimeout(() => setBulkMsg(null), 6000);
    }
  }

  const restaurantOptions = useMemo(() => {
    const set = new Set<string>();
    for (const r of matrix.rows) {
      const k = r.rest_brand
        ? `${r.rest_brand}${r.rest_branch ? ' · ' + r.rest_branch : ''}`
        : '— atanmamış —';
      set.add(k);
    }
    return Array.from(set).sort();
  }, [matrix.rows]);

  // Map: "brand · branch" string → restaurant_id (ilk eşleşen)
  const restaurantIdMap = useMemo(() => {
    const m = new Map<string, number>();
    for (const r of matrix.rows) {
      if (!r.rest_brand || !r.rest_id) continue;
      const k = `${r.rest_brand}${r.rest_branch ? ' · ' + r.rest_branch : ''}`;
      if (!m.has(k)) m.set(k, r.rest_id);
    }
    return m;
  }, [matrix.rows]);

  const selectedRestaurantId = restFilter ? restaurantIdMap.get(restFilter) : null;

  async function submitApproval() {
    if (submitBusy) return;
    if (!selectedRestaurantId) {
      setSubmitMsg('Önce bir restoran seçin (filtre).');
      setTimeout(() => setSubmitMsg(null), 4000);
      return;
    }
    if (!confirm(
      `${restFilter} için ${formatPeriod(period)} puantajını ONAYA gönder?\n` +
      `Admin onayladıktan sonra bordroya geçecek.`,
    )) return;
    setSubmitBusy(true);
    setSubmitMsg(null);
    try {
      const res: PuantajApproval = await submitPuantajApproval(
        selectedRestaurantId,
        period,
      );
      setSubmitMsg(
        `✓ Onaya gönderildi · ${res.entry_count} kayıt · ${tr(Math.round(res.total_hours))} sa · ${tr(res.total_packages)} paket`,
      );
      router.refresh();
    } catch (err) {
      setSubmitMsg(err instanceof Error ? err.message : 'Hata oluştu');
    } finally {
      setSubmitBusy(false);
      setTimeout(() => setSubmitMsg(null), 8000);
    }
  }

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    return matrix.rows.filter((r) => {
      if (hideSupport && r.is_support_row) return false;
      if (q) {
        const hay = `${r.full_name ?? ''} ${r.person_code ?? ''} ${r.rest_brand ?? ''} ${r.rest_branch ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      if (restFilter) {
        const k = r.rest_brand
          ? `${r.rest_brand}${r.rest_branch ? ' · ' + r.rest_branch : ''}`
          : '— atanmamış —';
        if (k !== restFilter) return false;
      }
      if (roleFilter && r.role !== roleFilter) return false;
      return true;
    });
  }, [matrix.rows, search, restFilter, roleFilter, hideSupport]);

  const counts = matrix.summary.cell_counts || {};
  const filteredHours = filtered.reduce((s, r) => s + r.total_hours, 0);
  const filteredPackages = filtered.reduce((s, r) => s + r.total_packages, 0);

  return (
    <>
      {/* Header */}
      <header className="flex justify-between items-end gap-5 flex-wrap mb-5">
        <div>
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Operasyon · <span className="text-brand">Puantaj</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            {formatPeriod(period)} Puantajı
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {matrix.summary.personnel_count} personel × {totalDays} gün ·{' '}
            {(counts.normal ?? 0) +
              (counts.izin ?? 0) +
              (counts.gelmedi ?? 0) +
              (counts.raporlu ?? 0)}{' '}
            kayıt
          </div>
        </div>
        <div className="flex gap-2 items-center flex-wrap">
          {/* Ay nav — dropdown ile tüm aylar */}
          <select
            value={period}
            onChange={(e) => {
              window.location.href = `/puantaj?ay=${e.target.value}`;
            }}
            className="px-3 py-1.5 rounded-xl bg-bg-surface border border-border text-[12.5px] font-semibold text-text-2 hover:border-text/30 transition cursor-pointer focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20"
          >
            {periods.map((p) => (
              <option key={p} value={p}>
                {formatPeriod(p)}
              </option>
            ))}
          </select>
          <button className="px-3 py-2 rounded-xl bg-bg-surface border border-border text-text-2 text-[13px] font-medium hover:border-text/30 transition flex items-center gap-1.5">
            <Copy className="w-3.5 h-3.5" strokeWidth={2.2} /> Geçen aydan kopyala
          </button>
          <button
            onClick={async () => {
              try {
                const params = new URLSearchParams({ period });
                if (selectedRestaurantId) {
                  params.set('restaurant_id', String(selectedRestaurantId));
                }
                const res = await fetch(`/api/puantaj/template?${params.toString()}`);
                if (!res.ok) throw new Error(`Şablon indirilemedi (${res.status})`);
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const restPart = restFilter ? `-${restFilter.replace(/\s+/g, '_')}` : '';
                a.download = `puantaj-sablon-${period}${restPart}.xlsx`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
              } catch (e) {
                alert(e instanceof Error ? e.message : 'Şablon indirilemedi');
              }
            }}
            className="px-3 py-2 rounded-xl bg-bg-surface border border-border text-text-2 text-[13px] font-medium hover:border-text/30 transition flex items-center gap-1.5"
            title={
              selectedRestaurantId
                ? `${restFilter} için ${formatPeriod(period)} şablonu indir`
                : `Tüm personel için ${formatPeriod(period)} şablonu indir`
            }
          >
            <ArrowDownToLine className="w-3.5 h-3.5" strokeWidth={2.2} /> Excel Şablonu
          </button>

          {/* Excel Yükle — gizli file input + tetikleyici buton */}
          <label className="px-3 py-2 rounded-xl bg-brand-soft border border-brand/30 text-brand text-[13px] font-semibold hover:bg-brand/15 transition flex items-center gap-1.5 cursor-pointer">
            <ArrowUpFromLine className="w-3.5 h-3.5" strokeWidth={2.2} />
            Excel Yükle
            <input
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className="hidden"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                if (!confirm(
                  `"${file.name}" dosyasını ${formatPeriod(period)} dönemine yüklemek istediğinden emin misin? ` +
                  `Mevcut hücreler dolduysa ÜZERİNE yazılır.`
                )) {
                  e.target.value = '';
                  return;
                }
                try {
                  const form = new FormData();
                  form.append('file', file);
                  const res = await fetch(
                    `/api/puantaj/template/import?period=${period}`,
                    { method: 'POST', body: form },
                  );
                  if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err?.detail ?? `Hata ${res.status}`);
                  }
                  const data = await res.json();
                  const p = data.puantaj || {};
                  const d = data.destek || {};
                  const msg = [
                    `✓ Yükleme tamamlandı`,
                    `Puantaj: +${p.inserted ?? 0} yeni, ${p.updated ?? 0} güncellendi, ${p.skipped ?? 0} atlandı`,
                    `Destek: +${d.inserted ?? 0} yeni, ${d.updated ?? 0} güncellendi, ${d.skipped ?? 0} atlandı`,
                  ];
                  const allErrors = [...(p.errors || []), ...(d.errors || [])];
                  if (allErrors.length > 0) {
                    msg.push('', `Hatalar (${allErrors.length}):`, ...allErrors.slice(0, 5).map((x: string) => `• ${x}`));
                    if (allErrors.length > 5) msg.push(`• ... ve ${allErrors.length - 5} tane daha`);
                  }
                  alert(msg.join('\n'));
                  window.location.reload();
                } catch (err) {
                  alert(err instanceof Error ? err.message : 'Yükleme başarısız');
                } finally {
                  e.target.value = '';
                }
              }}
            />
          </label>
          <button
            onClick={submitApproval}
            disabled={submitBusy || !selectedRestaurantId}
            title={
              selectedRestaurantId
                ? `${restFilter} için onaya gönder`
                : 'Önce bir restoran filtreleyin'
            }
            className="px-4 py-2 rounded-xl bg-brand text-white text-[13px] font-semibold shadow-sm hover:bg-brand-dark transition flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitBusy ? (
              <Loader2 className="w-4 h-4 animate-spin" strokeWidth={2.2} />
            ) : (
              <Send className="w-4 h-4" strokeWidth={2.2} />
            )}
            Onaya Gönder
          </button>
        </div>
      </header>

      {/* Onay banner */}
      {submitMsg && (
        <div
          className={`mb-3 px-4 py-2.5 rounded-xl text-[13px] font-medium border flex items-center gap-2 ${
            submitMsg.startsWith('✓')
              ? 'bg-green-50 border-green-200 text-green-800'
              : 'bg-red-50 border-red-200 text-red-700'
          }`}
        >
          {submitMsg.startsWith('✓') ? (
            <ShieldCheck className="w-4 h-4" strokeWidth={2.2} />
          ) : (
            <AlertCircle className="w-4 h-4" strokeWidth={2.2} />
          )}
          {submitMsg}
        </div>
      )}

      {/* Stats Bar — 5 cell */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
        <StatCard
          label="Toplam Saat"
          value={tr(Math.round(matrix.summary.total_hours))}
          meta={`${tr(Math.round(matrix.summary.total_hours / Math.max(matrix.summary.personnel_count, 1)))} sa/kurye ortalama`}
          accent="brand"
        />
        <StatCard
          label="Toplam Paket"
          value={tr(matrix.summary.total_packages)}
          meta={`${matrix.summary.worked_days} gün çalışıldı`}
          accent="success"
        />
        <StatCard
          label="Çalışılan Gün"
          value={tr(matrix.summary.worked_days)}
          meta={`${counts.izin ?? 0} izin · ${counts.empty ?? 0} boş`}
          accent="cream"
        />
        <StatCard
          label="Joker / Destek Cover"
          value={tr(matrix.summary.joker_days)}
          meta="başka restorana destek günü"
          accent="warn"
        />
        <StatCard
          label="Eksik / Sorunlu"
          value={tr(
            (counts.gelmedi ?? 0) +
              (counts.raporlu ?? 0) +
              (counts.ihbarsiz ?? 0),
          )}
          meta={`${counts.gelmedi ?? 0} gelmedi · ${counts.raporlu ?? 0} raporlu`}
          accent="danger"
        />
      </div>

      {/* Filters */}
      <div className="flex gap-2 items-center mb-3 flex-wrap">
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Personel ara…"
          className="px-3 py-1.5 rounded-lg border border-border text-sm w-64 bg-bg-surface focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
        />
        <select
          value={restFilter ?? ''}
          onChange={(e) => setRestFilter(e.target.value || null)}
          className="px-3 py-1.5 rounded-lg border border-border text-sm bg-bg-surface focus:outline-none focus:border-brand transition"
        >
          <option value="">Tüm Restoranlar</option>
          {restaurantOptions.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <select
          value={roleFilter ?? ''}
          onChange={(e) => setRoleFilter(e.target.value || null)}
          className="px-3 py-1.5 rounded-lg border border-border text-sm bg-bg-surface focus:outline-none focus:border-brand transition"
        >
          <option value="">Tüm Roller</option>
          <option value="Kurye">Kurye</option>
          <option value="Joker">Joker</option>
          <option value="Bölge Müdürü">Bölge Müdürü</option>
          <option value="Kaptan">Kaptan</option>
          <option value="Restoran Takım Şefi">Takım Şefi</option>
        </select>
        <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-[12.5px] text-text-2 bg-bg-surface cursor-pointer hover:border-text/30 transition select-none">
          <input
            type="checkbox"
            checked={hideSupport}
            onChange={(e) => setHideSupport(e.target.checked)}
            className="w-3.5 h-3.5 accent-orange-500"
          />
          <span>Destek satırını gizle</span>
        </label>
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
          {filtered.length} sonuç · {tr(Math.round(filteredHours))} sa ·{' '}
          {tr(filteredPackages)} paket
        </span>
      </div>

      {/* GRID */}
      <div className="bg-bg-surface border border-border rounded-2xl shadow-md overflow-hidden">
        <div className="overflow-auto max-h-[calc(100vh-340px)]">
          <table className="grid-table border-separate border-spacing-0 text-[12px] min-w-full">
            <thead className="sticky top-0 z-30">
              <tr>
                <th className="col-person sticky left-0 z-[31] bg-cream-50 border-b-2 border-border-2 px-3.5 py-2.5 text-left font-semibold text-[10px] uppercase tracking-wider text-text-3 min-w-[230px] max-w-[230px]">
                  Personel
                </th>
                <th className="col-rest sticky left-[230px] z-[31] bg-cream-50 border-b-2 border-r-2 border-border-2 px-3 py-2.5 text-left font-semibold text-[10px] uppercase tracking-wider text-text-3 min-w-[150px] max-w-[150px]">
                  Restoran
                </th>
                {Array.from({ length: totalDays }, (_, i) => i + 1).map((d) => {
                  const dow = dayOfWeek(period, d);
                  const isWE = dow === 0 || dow === 6;
                  const today = isToday(period, d);
                  return (
                    <th
                      key={d}
                      className={`day-h border-b-2 border-border-2 px-1 py-1.5 text-center align-bottom min-w-[38px] ${
                        today
                          ? 'bg-brand text-white'
                          : isWE
                          ? 'bg-brand-soft/60'
                          : 'bg-cream-50'
                      }`}
                    >
                      <span
                        className={`block font-mono text-[13px] font-bold ${
                          today ? 'text-white' : 'text-text'
                        }`}
                      >
                        {d}
                      </span>
                      <span
                        className={`block text-[9px] mt-0.5 font-semibold ${
                          today
                            ? 'text-white/85'
                            : isWE
                            ? 'text-brand'
                            : 'text-text-3'
                        }`}
                      >
                        {TR_DAYS[dow]}
                      </span>
                    </th>
                  );
                })}
                <th className="col-total sticky right-0 z-[31] bg-cream-50 border-b-2 border-l-2 border-border-2 px-3.5 py-2.5 text-right font-semibold text-[10px] uppercase tracking-wider text-text-3 min-w-[130px] max-w-[130px]">
                  Toplam
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <PersonRow
                  key={row.row_key ?? `${row.id}-${row.is_support_row ? 'd' : 'm'}-${row.rest_id ?? 'x'}`}
                  row={row}
                  totalDays={totalDays}
                  period={period}
                  onCellClick={(day, cell, target) => {
                    const rect = (target as HTMLElement).getBoundingClientRect();
                    setEditing({
                      row,
                      day,
                      cell,
                      pos: { x: rect.right + 8, y: rect.top },
                    });
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-3.5 px-5 py-3 bg-cream-50 border-t border-border text-[11.5px] text-text-2">
          <Legend swatch="bg-gradient-to-b from-green-50 to-white" label="Normal" />
          <Legend swatch="bg-cream-100" label="İzin" />
          <Legend swatch="bg-red-50" label="Gelmedi" />
          <Legend swatch="bg-yellow-50" label="Raporlu" />
          <Legend swatch="bg-gradient-to-br from-red-50 to-cream-100" label="İhbarsız" />
          <Legend
            swatch="bg-orange-100 border-l-2 border-orange-500"
            label="Destek satırı"
          />
          <Legend
            swatch="bg-white"
            label="Bugün"
            ringClass="ring-[2px] ring-brand ring-inset"
          />
          <span className="ml-auto text-text-3 text-[11px]">
            Hücreye tıklayıp düzenle · destek için ↪ rozetli satır
          </span>
        </div>
      </div>

      {/* Sticky bottom action bar */}
      <div className="fixed bottom-0 left-[252px] right-0 bg-text text-white px-8 py-3 flex items-center justify-between gap-3 z-40 shadow-[0_-8px_24px_rgba(0,0,0,0.12)]">
        <div className="flex gap-3 items-center flex-wrap">
          <span className="text-[12px] text-white/70">
            <strong className="text-white">Hızlı doldur:</strong>
          </span>
          <button
            onClick={() => runBulk('all', 9)}
            disabled={bulkBusy}
            className="px-3 py-1.5 rounded-lg bg-white/10 border border-white/15 text-[12.5px] font-medium hover:bg-white/20 transition disabled:opacity-50"
            title="Tüm aktif kuryelere uygula"
          >
            Tüm gün · 9 saat
          </button>
          <button
            onClick={() => runBulk('weekend_off', 9)}
            disabled={bulkBusy}
            className="px-3 py-1.5 rounded-lg bg-white/10 border border-white/15 text-[12.5px] font-medium hover:bg-white/20 transition disabled:opacity-50"
          >
            Hafta sonu boş
          </button>
          <button
            onClick={() => runBulk('copy_previous')}
            disabled={bulkBusy}
            className="px-3 py-1.5 rounded-lg bg-white/10 border border-white/15 text-[12.5px] font-medium hover:bg-white/20 transition disabled:opacity-50"
          >
            Geçen aydan kopyala
          </button>
          <span className="w-px h-5 bg-white/20" />
          {/* Filtreli doldurma — sadece görünümdeki kişilere */}
          <span className="text-[11px] text-yellow-200 font-semibold">Görünüme:</span>
          <button
            onClick={() => runBulk('all', 9, 'view')}
            disabled={bulkBusy || filtered.length === 0}
            className="px-3 py-1.5 rounded-lg bg-yellow-400/20 border border-yellow-400/40 text-yellow-100 text-[12.5px] font-medium hover:bg-yellow-400/30 transition disabled:opacity-50"
            title={`Filtrelenmiş ${filtered.filter((r) => !r.is_support_row).length} kişiye 9 saat × tüm gün`}
          >
            Bu görünümü 9sa
          </button>
          <button
            onClick={() => runBulk('weekend_off', 9, 'view')}
            disabled={bulkBusy || filtered.length === 0}
            className="px-3 py-1.5 rounded-lg bg-yellow-400/20 border border-yellow-400/40 text-yellow-100 text-[12.5px] font-medium hover:bg-yellow-400/30 transition disabled:opacity-50"
          >
            Hafta sonu boş
          </button>
          <span className="w-px h-5 bg-white/20" />
          <span className="text-[12px] text-white/75 inline-flex items-center gap-1">
            <BarChart3 className="w-3.5 h-3.5" strokeWidth={2.2} /> Toplam:{' '}
            <strong className="text-white font-mono">
              {tr(Math.round(matrix.summary.total_hours))} sa ·{' '}
              {tr(matrix.summary.total_packages)} paket
            </strong>
          </span>
        </div>
        <div className="flex gap-2 items-center">
          <span className="text-[11.5px] text-white/60 inline-flex items-center gap-1">
            {bulkMsg ?? (bulkBusy ? (
              <><Loader2 className="w-3 h-3 animate-spin" strokeWidth={2.2} /> Doldur işlemi…</>
            ) : (
              <><Check className="w-3 h-3" strokeWidth={2.4} /> Otomatik kaydedildi</>
            ))}
          </span>
        </div>
      </div>

      {editing && (
        <CellPopover
          row={editing.row}
          day={editing.day}
          cell={editing.cell}
          pos={editing.pos}
          period={period}
          onClose={() => setEditing(null)}
          onSaved={(newCell) =>
            updateLocalCell(editing.row.id, editing.row.row_key, editing.day, newCell)
          }
        />
      )}
    </>
  );
}

function StatCard({
  label, value, meta, accent,
}: {
  label: string;
  value: string;
  meta?: string;
  accent: 'brand' | 'success' | 'warn' | 'danger' | 'cream';
}) {
  const accentMap: Record<string, string> = {
    brand: 'bg-brand',
    success: 'bg-green-500',
    warn: 'bg-yellow-500',
    danger: 'bg-red-500',
    cream: 'bg-yellow-700',
  };
  return (
    <div className="relative bg-bg-surface border border-border rounded-2xl px-5 py-3.5 shadow-sm overflow-hidden">
      <div
        className={`absolute left-0 top-0 bottom-0 w-[3px] ${accentMap[accent]}`}
      />
      <div className="text-[11px] uppercase tracking-wider text-text-3 font-semibold mb-1.5">
        {label}
      </div>
      <div className="font-display text-[24px] font-bold tracking-tight leading-none num">
        {value}
      </div>
      {meta && (
        <div className="text-[11px] text-text-3 mt-1.5">{meta}</div>
      )}
    </div>
  );
}

function Legend({
  swatch, label, ringClass,
}: {
  swatch: string;
  label: string;
  ringClass?: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`w-4 h-4 rounded ${swatch} ${ringClass ?? ''}`}
      />
      <span>{label}</span>
    </div>
  );
}

function PersonRow({
  row, totalDays, period, onCellClick,
}: {
  row: MatrixRow;
  totalDays: number;
  period: string;
  onCellClick: (day: number, cell: MatrixCell, target: EventTarget) => void;
}) {
  const initials = (row.full_name ?? '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
  const av = avatarClass(row.role);

  const isSupport = row.is_support_row;
  const rowBg = isSupport ? 'bg-orange-50/40' : 'bg-bg-surface';
  const rowHoverBg = isSupport ? 'group-hover:bg-orange-100/60' : 'group-hover:bg-brand-mist/40';

  return (
    <tr className={`hover:bg-bg-surface2/50 group ${isSupport ? 'border-l-2 border-l-orange-300' : ''}`}>
      {/* Personel cell — sticky left */}
      <td className={`col-person sticky left-0 z-[20] ${rowBg} border-b border-r-2 border-border-2 px-3.5 py-2.5 ${rowHoverBg} transition min-w-[230px] max-w-[230px] ${isSupport ? 'pl-7' : ''}`}>
        <div className="flex items-center gap-2.5">
          {isSupport && (
            <div className="absolute left-2 top-1/2 -translate-y-1/2 text-orange-500 font-bold text-sm">↪</div>
          )}
          <div
            className={`w-8 h-8 rounded-full ${AV_COLORS[av]} font-bold flex items-center justify-center text-[11px] flex-shrink-0 ${isSupport ? 'opacity-70' : ''}`}
          >
            {initials || '?'}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5 min-w-0">
              <span className={`font-semibold text-[12.5px] truncate ${isSupport ? 'text-text-2' : 'text-text'}`}>
                {row.full_name ?? '—'}
              </span>
              {isSupport && (
                <span className="px-1.5 py-px rounded text-[9px] font-bold bg-orange-100 text-orange-700 border border-orange-300 flex-shrink-0">
                  DESTEK
                </span>
              )}
            </div>
            <div className="text-[10.5px] font-mono text-text-3">
              {row.person_code ?? ''}
            </div>
          </div>
        </div>
      </td>
      {/* Restoran — sticky */}
      <td className={`col-rest sticky left-[230px] z-[19] ${rowBg} border-b border-r-2 border-border-2 px-3 py-2.5 ${rowHoverBg} transition min-w-[150px] max-w-[150px]`}>
        <div className={`text-[11.5px] font-medium truncate ${isSupport ? 'text-orange-700' : 'text-text-2'}`}>
          {row.rest_brand
            ? `${row.rest_brand}${row.rest_branch ? ' · ' + row.rest_branch : ''}`
            : (
              <span className="text-text-3 italic">— atanmamış —</span>
            )}
        </div>
      </td>
      {/* Gün hücreleri */}
      {Array.from({ length: totalDays }, (_, i) => i + 1).map((day) => {
        const cell = row.cells[day - 1] ?? { type: 'empty', hours: 0, packages: 0, is_support: false, restaurant_id: null };
        const dow = dayOfWeek(period, day);
        const isWE = dow === 0 || dow === 6;
        const today = isToday(period, day);
        return (
          <td
            key={day}
            className="border-b border-border p-0 align-middle"
            onClick={(e) => onCellClick(day, cell, e.currentTarget)}
          >
            <Cell cell={cell} weekend={isWE} today={today} />
          </td>
        );
      })}
      {/* Toplam — sticky right */}
      <td className="col-total sticky right-0 z-[19] bg-cream-50/70 border-b border-l-2 border-border-2 px-3.5 py-2.5 text-right group-hover:bg-cream-100 transition min-w-[130px] max-w-[130px]">
        <div className="flex flex-col items-end gap-0.5">
          <div className="text-[11.5px]">
            <span className="font-mono font-bold text-[13px]">
              {tr(Math.round(row.total_hours))}
            </span>
            <span className="text-text-3"> sa · </span>
            <span className="font-mono font-bold text-[13px]">
              {tr(row.total_packages)}
            </span>
            <span className="text-text-3"> pkt</span>
          </div>
          <div className="text-[10px] text-text-3 font-semibold uppercase tracking-wider">
            {row.worked_days} gün
            {row.joker_days > 0 ? ` · ${row.joker_days} destek` : ''}
          </div>
        </div>
      </td>
    </tr>
  );
}

function Cell({
  cell, weekend, today,
}: {
  cell: MatrixCell;
  weekend: boolean;
  today: boolean;
}) {
  const t = cell.type;

  let bg = 'bg-white';
  let content: React.ReactNode = null;

  if (t === 'normal') {
    bg = 'bg-gradient-to-b from-green-50 to-white';
    content = (
      <>
        <span className="font-mono text-[11px] font-bold text-text leading-none">
          {cell.hours}
        </span>
        <span className="font-mono text-[9.5px] text-text-3 font-semibold leading-none">
          {cell.packages > 0 ? cell.packages : '—'}
        </span>
        {cell.is_support && (
          <span className="absolute top-[2px] right-[2px] w-1.5 h-1.5 rounded-full bg-blue-500 ring-[1.5px] ring-white" />
        )}
      </>
    );
  } else if (t === 'izin') {
    bg = 'bg-cream-100';
    content = <StPlane className="w-3 h-3 text-yellow-700" strokeWidth={2.2} />;
  } else if (t === 'gelmedi') {
    bg = 'bg-red-50';
    content = <StX className="w-3.5 h-3.5 text-red-600" strokeWidth={2.4} />;
  } else if (t === 'raporlu') {
    bg = 'bg-yellow-50';
    content = <StSteth className="w-3 h-3 text-yellow-700" strokeWidth={2.2} />;
  } else if (t === 'ihbarsiz') {
    bg = 'bg-gradient-to-br from-red-50 to-cream-100';
    content = <StAlert className="w-3 h-3 text-red-700" strokeWidth={2.4} />;
  }

  // Weekend pattern for empty cells
  const weekendBg =
    weekend && t === 'empty'
      ? 'bg-[repeating-linear-gradient(45deg,transparent_0,transparent_4px,rgba(15,82,186,0.05)_4px,rgba(15,82,186,0.05)_8px)]'
      : '';

  return (
    <div
      className={`relative w-[38px] h-[56px] flex flex-col items-center justify-center gap-px border-r border-border cursor-pointer transition-all hover:scale-[1.06] hover:z-10 hover:shadow-md hover:rounded-md ${bg} ${weekendBg} ${
        today ? 'shadow-[inset_0_0_0_2px_var(--brand,#0F52BA)]' : ''
      } ${
        cell.is_support && t === 'normal'
          ? 'shadow-[inset_0_0_0_2px_#3B82F6]'
          : ''
      }`}
    >
      {content}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────
// Cell Popover — hücre düzenleme
// ──────────────────────────────────────────────────────────────────

import {
  AlertCircle as StAlert, CheckCircle2 as StCheck, Minus as StMinus,
  Plane as StPlane, Stethoscope as StSteth, XCircle as StX,
  type LucideIcon,
} from 'lucide-react';

type StatusKey = 'normal' | 'izin' | 'gelmedi' | 'raporlu' | 'ihbarsiz' | 'empty';
const STATUSES: { key: StatusKey; label: string; Icon: LucideIcon }[] = [
  { key: 'normal', label: 'Normal', Icon: StCheck },
  { key: 'izin', label: 'İzin', Icon: StPlane },
  { key: 'gelmedi', label: 'Gelmedi', Icon: StX },
  { key: 'raporlu', label: 'Raporlu', Icon: StSteth },
  { key: 'ihbarsiz', label: 'İhbarsız', Icon: StAlert },
  { key: 'empty', label: 'Boş', Icon: StMinus },
];

function CellPopover({
  row, day, cell, pos, period, onClose, onSaved,
}: {
  row: MatrixRow;
  day: number;
  cell: MatrixCell;
  pos: { x: number; y: number };
  period: string;
  onClose: () => void;
  onSaved?: (newCell: MatrixCell) => void;
}) {
  const router = useRouter();
  const [status, setStatus] = useState<typeof STATUSES[number]['key']>(cell.type);
  const [hours, setHours] = useState<number>(cell.hours || 0);
  const [packages, setPackages] = useState<number>(cell.packages || 0);
  const [isSupport, setIsSupport] = useState<boolean>(cell.is_support);
  const [coversId, setCoversId] = useState<number | null>(
    cell.covers_personnel_id ?? null,
  );
  const [candidates, setCandidates] = useState<ReplacementCandidatesResponse | null>(null);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAbsence = status === 'gelmedi' || status === 'raporlu' || status === 'ihbarsiz';

  // Absence seçilince adayları yükle (cell'in restoran id'sinden)
  useEffect(() => {
    if (!isAbsence) return;
    const rid = cell.restaurant_id ?? row.rest_id;
    if (!rid || candidates) return;
    setCandidatesLoading(true);
    getReplacementCandidates(rid)
      .then(setCandidates)
      .catch(() => setCandidates(null))
      .finally(() => setCandidatesLoading(false));
  }, [isAbsence, cell.restaurant_id, row.rest_id, candidates]);

  // Tarih: YYYY-MM-DD
  const [y, m] = period.split('-');
  const dateStr = `${y}-${m}-${String(day).padStart(2, '0')}`;
  const dateTr = `${day} ${TR_MONTHS[parseInt(m, 10) - 1]} ${y}`;
  const restName = row.rest_brand
    ? `${row.rest_brand}${row.rest_branch ? ' · ' + row.rest_branch : ''}`
    : '— atanmamış —';

  // ESC ile kapat
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  // Status değişince saat/paket sıfırla; absence dışı ise coversId temizle
  useEffect(() => {
    if (status !== 'normal') {
      setHours(0);
      setPackages(0);
    }
    if (status !== 'gelmedi' && status !== 'raporlu' && status !== 'ihbarsiz') {
      setCoversId(null);
    }
  }, [status]);

  // Konumu ekran sınırları içinde tut
  const popX = Math.min(pos.x, window.innerWidth - 320);
  const popY = Math.min(pos.y, window.innerHeight - 380);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await updatePuantajCell({
        personnel_id: row.id,
        entry_date: dateStr,
        cell_type: status,
        worked_hours: hours,
        package_count: packages,
        // Destek satırından düzenleniyorsa o restoran ID'sine yaz, ayrıca Destek coverage
        restaurant_id: row.is_support_row ? row.rest_id ?? undefined : undefined,
        coverage_type:
          status === 'normal' && (isSupport || row.is_support_row)
            ? 'Destek'
            : undefined,
        covers_personnel_id: isAbsence ? coversId : null,
      });
      // Optimistic: lokal state'i güncelle, refresh GEREK YOK
      const coversName = candidates && coversId
        ? [
            ...(candidates.same_restaurant || []),
            ...(candidates.jokers || []),
            ...(candidates.management || []),
          ].find((c) => c.id === coversId)?.full_name ?? null
        : null;
      const coversRole = candidates && coversId
        ? [
            ...(candidates.same_restaurant || []),
            ...(candidates.jokers || []),
            ...(candidates.management || []),
          ].find((c) => c.id === coversId)?.role ?? null
        : null;
      onSaved?.({
        type: status,
        hours: status === 'normal' ? hours : 0,
        packages: status === 'normal' ? packages : 0,
        is_support: status === 'normal' ? (isSupport || row.is_support_row) : cell.is_support,
        restaurant_id: cell.restaurant_id,
        covers_personnel_id: isAbsence ? coversId : null,
        covers_personnel_name: isAbsence ? coversName : null,
        covers_personnel_role: isAbsence ? coversRole : null,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kaydedilemedi');
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      {/* Backdrop (tıklayınca kapat) */}
      <div
        className="fixed inset-0 z-[90]"
        onClick={onClose}
      />
      {/* Popover */}
      <div
        className="fixed z-[100] bg-bg-surface border border-border rounded-xl shadow-2xl w-[300px] p-4 animate-pop-in"
        style={{ left: popX, top: Math.max(20, popY) }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-1">
          <div className="font-display text-[14px] font-semibold tracking-tight">
            {row.full_name}
          </div>
          <button
            onClick={onClose}
            className="text-text-3 hover:text-text text-lg leading-none w-6 h-6 flex items-center justify-center rounded hover:bg-bg-surface2"
          >
            ×
          </button>
        </div>
        <div className="text-[11.5px] text-text-3 mb-3">
          {dateTr} · {restName}
        </div>

        {/* Status grid */}
        <div className="grid grid-cols-3 gap-1.5 mb-3">
          {STATUSES.map((s) => {
            const active = status === s.key;
            return (
              <button
                key={s.key}
                type="button"
                onClick={() => setStatus(s.key)}
                className={`px-2 py-2 rounded-md border-[1.5px] text-[11px] font-semibold flex flex-col items-center gap-0.5 transition ${
                  active
                    ? 'border-brand bg-brand-soft text-brand'
                    : 'border-border hover:border-text-3 text-text-2'
                }`}
              >
                <s.Icon className="w-3.5 h-3.5" strokeWidth={2.2} />
                <span>{s.label}</span>
              </button>
            );
          })}
        </div>

        {/* Saat & paket — sadece normal aktif */}
        <div className="grid grid-cols-2 gap-2 mb-3">
          <label className="block">
            <div className="text-[10.5px] text-text-3 font-semibold mb-1">
              Saat
            </div>
            <input
              type="number"
              step="any"
              min={0}
              value={hours || ''}
              onChange={(e) => setHours(parseFloat(e.target.value) || 0)}
              disabled={status !== 'normal'}
              className="w-full px-2.5 py-1.5 rounded-md border border-border bg-bg-surface2 text-[13px] font-mono font-semibold disabled:opacity-50"
            />
          </label>
          <label className="block">
            <div className="text-[10.5px] text-text-3 font-semibold mb-1">
              Paket
            </div>
            <input
              type="number"
              min={0}
              value={packages || ''}
              onChange={(e) => setPackages(parseInt(e.target.value, 10) || 0)}
              disabled={status !== 'normal'}
              className="w-full px-2.5 py-1.5 rounded-md border border-border bg-bg-surface2 text-[13px] font-mono font-semibold disabled:opacity-50"
            />
          </label>
        </div>

        {/* Destek toggle (Normal'da) */}
        {status === 'normal' && (
          <label className="flex items-center gap-2 cursor-pointer mb-3 p-2 -mx-1 rounded-md hover:bg-bg-surface2">
            <input
              type="checkbox"
              checked={isSupport}
              onChange={(e) => setIsSupport(e.target.checked)}
              className="w-4 h-4 accent-brand"
            />
            <span className="text-[12px] text-text-2">
              ↪ Destek vardiyası (kuryenin kendi restoranı dışında)
            </span>
          </label>
        )}

        {/* Yerine kim girdi? — sadece absence status'larda */}
        {isAbsence && (
          <div className="mb-3 -mx-1 p-2 rounded-md bg-amber-50/60 border border-amber-200">
            <div className="text-[10.5px] font-bold uppercase tracking-wider text-amber-900 mb-1.5">
              Yerine kim girdi?
            </div>
            {candidatesLoading ? (
              <div className="text-[11.5px] text-text-3 italic">
                Yükleniyor…
              </div>
            ) : (
              <select
                value={coversId ?? ''}
                onChange={(e) => setCoversId(e.target.value ? parseInt(e.target.value, 10) : null)}
                className="w-full px-2 py-1.5 rounded-md border border-amber-300 bg-white text-[12px] focus:outline-none focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
              >
                <option value="">— Yerine kimse girmedi —</option>
                {candidates?.same_restaurant && candidates.same_restaurant.length > 0 && (
                  <optgroup label="Destek · Aynı restoran kuryesi (ücretli)">
                    {candidates.same_restaurant
                      .filter((c) => c.id !== row.id)
                      .map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.full_name} ({c.person_code})
                        </option>
                      ))}
                  </optgroup>
                )}
                {candidates?.other_restaurant_couriers && candidates.other_restaurant_couriers.length > 0 && (
                  <optgroup label="Destek · Diğer restoran kuryesi (ücretli)">
                    {candidates.other_restaurant_couriers.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.full_name} ({c.person_code}) — {c.rest_brand}
                        {c.rest_branch ? ` / ${c.rest_branch}` : ''}
                      </option>
                    ))}
                  </optgroup>
                )}
                {((candidates?.jokers?.length ?? 0) + (candidates?.management?.length ?? 0)) > 0 && (
                  <optgroup label="Yönetim · Joker / BM / Kaptan / RTŞ (ücretsiz kapama)">
                    {candidates?.jokers?.map((c) => (
                      <option key={`j-${c.id}`} value={c.id}>
                        {c.full_name} — Joker
                      </option>
                    ))}
                    {candidates?.management?.map((c) => (
                      <option key={`m-${c.id}`} value={c.id}>
                        {c.full_name} — {c.role}
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
            )}
            <div className="mt-1.5 text-[10px] text-amber-900/80 leading-snug">
              Hakediş kişinin rolüne göre hesaplanır:{' '}
              <strong>Kurye / RTŞ / Kaptan</strong> başka restorana gidince
              paket × tarife EKSTRA hakediş alır. <strong>BM / Joker</strong>{' '}
              sabit maaşlı — ekstra ücret YOK. Her durumda restorana fatura yansır.
            </div>
            {cell.covers_personnel_name && coversId === cell.covers_personnel_id && (
              <div className="mt-1.5 text-[11px] text-amber-800">
                Şu an seçili: <strong>{cell.covers_personnel_name}</strong>
                {cell.covers_personnel_role && ` (${cell.covers_personnel_role})`}
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-2 text-red-700 text-[11.5px] mb-3">
            {error}
          </div>
        )}

        {/* Butonlar */}
        <div className="flex gap-1.5">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-3 py-1.5 rounded-md text-[12px] font-semibold border border-border bg-bg-surface text-text-2 hover:bg-bg-surface2 transition"
            disabled={saving}
          >
            İptal
          </button>
          <button
            type="button"
            onClick={save}
            disabled={saving}
            className="flex-1 px-3 py-1.5 rounded-md text-[12px] font-semibold bg-brand text-white shadow-sm hover:bg-brand-dark transition disabled:opacity-60"
          >
            {saving ? 'Kaydediliyor…' : 'Kaydet'}
          </button>
        </div>

        <style jsx>{`
          @keyframes pop-in {
            from { opacity: 0; transform: scale(0.96); }
            to { opacity: 1; transform: scale(1); }
          }
          :global(.animate-pop-in) {
            animation: pop-in 0.18s ease-out;
          }
        `}</style>
      </div>
    </>
  );
}
