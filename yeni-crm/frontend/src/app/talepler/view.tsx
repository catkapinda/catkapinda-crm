'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, Banknote, Bike, Building2, Calculator, Check, Clock,
  Plus, Search, Trash2, User, X, XCircle, type LucideIcon,
} from 'lucide-react';

import {
  type CourierRequest,
  type CourierRequestCounts,
  type Personnel,
  decideCourierRequest,
  deleteCourierRequest,
} from '@/lib/api';

import { NewRequestModal } from './new-modal';

// ─── Helpers ───────────────────────────────────────────────────────
const TYPES = ['Avans', 'Motor Değişikliği', 'Muhasebe Değişimi'] as const;
type ReqType = (typeof TYPES)[number] | 'all';
type StatusKey = 'Beklemede' | 'Onaylandı' | 'Reddedildi';

function tr(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function relTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  const diff = Date.now() - t;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return 'az önce';
  if (min < 60) return `${min} dk önce`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} saat önce`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} gün önce`;
  return new Date(iso).toLocaleDateString('tr-TR');
}

const TYPE_META: Record<string, { Icon: LucideIcon; bg: string; text: string; soft: string }> = {
  'Avans': {
    Icon: Banknote,
    bg: 'bg-green-600',
    text: 'text-green-700',
    soft: 'bg-green-50 border-green-200',
  },
  'Motor Değişikliği': {
    Icon: Bike,
    bg: 'bg-orange-600',
    text: 'text-orange-700',
    soft: 'bg-orange-50 border-orange-200',
  },
  'Muhasebe Değişimi': {
    Icon: Calculator,
    bg: 'bg-purple-600',
    text: 'text-purple-700',
    soft: 'bg-purple-50 border-purple-200',
  },
};

const AVATAR_GRADIENTS = [
  'from-blue-700 to-blue-500',
  'from-blue-900 to-blue-700',
  'from-yellow-600 to-yellow-400',
  'from-slate-700 to-slate-500',
  'from-purple-700 to-purple-500',
  'from-green-700 to-green-500',
];

// ─── Main view ─────────────────────────────────────────────────────
export function TaleplerView({
  requests, personnel, initialCounts,
}: {
  requests: CourierRequest[];
  personnel: Personnel[];
  initialCounts: CourierRequestCounts | null;
}) {
  const router = useRouter();
  const [statusTab, setStatusTab] = useState<StatusKey>('Beklemede');
  const [typeFilter, setTypeFilter] = useState<ReqType>('all');
  const [search, setSearch] = useState('');
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const counts = useMemo(() => {
    const c = { Beklemede: 0, Onaylandı: 0, Reddedildi: 0, total: requests.length };
    for (const r of requests) {
      if (r.status in c) c[r.status as StatusKey]++;
    }
    return c;
  }, [requests]);

  const typeCounts = useMemo(() => {
    const c: Record<string, number> = { Avans: 0, 'Motor Değişikliği': 0, 'Muhasebe Değişimi': 0 };
    for (const r of requests) {
      if (r.status === 'Beklemede' && r.request_type in c) {
        c[r.request_type]++;
      }
    }
    return c;
  }, [requests]);

  const totalAvans = useMemo(() => {
    return requests
      .filter((r) => r.status === 'Beklemede' && r.request_type === 'Avans')
      .reduce((s, r) => s + (r.amount || 0), 0);
  }, [requests]);

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    return requests.filter((r) => {
      if (r.status !== statusTab) return false;
      if (typeFilter !== 'all' && r.request_type !== typeFilter) return false;
      if (q) {
        const hay = `${r.personnel_name ?? ''} ${r.person_code ?? ''} ${r.reason ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [requests, statusTab, typeFilter, search]);

  async function handleDecide(id: number, status: 'Onaylandı' | 'Reddedildi') {
    if (busyId != null) return;
    if (!confirm(`Bu talebi ${status === 'Onaylandı' ? 'ONAYLAMAK' : 'REDDETMEK'} istediğine emin misin?`)) return;
    setBusyId(id);
    setError(null);
    try {
      await decideCourierRequest(id, { status });
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Karar uygulanamadı');
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id: number) {
    if (busyId != null) return;
    if (!confirm('Bu talep tamamen silinecek. Devam edilsin mi?')) return;
    setBusyId(id);
    setError(null);
    try {
      await deleteCourierRequest(id);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Silinemedi');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      {/* HEADER */}
      <header className="flex justify-between items-end gap-5 flex-wrap mb-6">
        <div>
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Operasyon · <span className="text-brand font-semibold">Talepler</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            Kurye Talepleri
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {counts.Beklemede} bekleyen · {counts.Onaylandı} onaylanan · {counts.Reddedildi} reddedilen ·
            avans bekleyen toplam <strong className="text-brand">{tr(totalAvans)} ₺</strong>
          </div>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="px-4 py-2 rounded-xl bg-brand text-white text-[13px] font-semibold shadow-sm hover:bg-brand-dark transition flex items-center gap-1.5"
        >
          <Plus className="w-4 h-4" strokeWidth={2.4} /> Yeni Talep
        </button>
      </header>

      {/* HERO STRIP — 4 KPI */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        <KpiCard
          icon={<Clock className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="brand"
          label="Bekleyen Toplam"
          value={String(counts.Beklemede)}
          sub="onay bekliyor"
        />
        <KpiCard
          icon={<Banknote className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="success"
          label="Avans"
          value={String(typeCounts.Avans)}
          sub={`${tr(totalAvans)} ₺ talep`}
        />
        <KpiCard
          icon={<Bike className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="warn"
          label="Motor Değişikliği"
          value={String(typeCounts['Motor Değişikliği'])}
          sub="bekliyor"
        />
        <KpiCard
          icon={<Calculator className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="purple"
          label="Muhasebe Değişimi"
          value={String(typeCounts['Muhasebe Değişimi'])}
          sub="bekliyor"
        />
      </div>

      {/* STATUS TABS + TYPE FILTER */}
      <div className="bg-white border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2 sticky top-2 z-10 backdrop-blur-sm">
        {/* Status tabs */}
        <div className="flex items-center gap-1 bg-bg-surface2 rounded-lg p-1">
          {(['Beklemede', 'Onaylandı', 'Reddedildi'] as StatusKey[]).map((s) => {
            const active = statusTab === s;
            const tone = s === 'Beklemede' ? 'brand' : s === 'Onaylandı' ? 'green' : 'red';
            return (
              <button
                key={s}
                onClick={() => setStatusTab(s)}
                className={`px-3 py-1.5 rounded-md text-[12.5px] font-semibold transition flex items-center gap-1.5 ${
                  active
                    ? tone === 'brand'
                      ? 'bg-brand text-white shadow'
                      : tone === 'green'
                      ? 'bg-green-600 text-white shadow'
                      : 'bg-red-600 text-white shadow'
                    : 'text-text-2 hover:bg-white'
                }`}
              >
                {s}
                <span className={`px-1.5 py-px rounded-full text-[10px] tabular-nums ${
                  active ? 'bg-white/25 text-white' : 'bg-bg-surface text-text-3'
                }`}>
                  {counts[s]}
                </span>
              </button>
            );
          })}
        </div>

        {/* Type filter */}
        <div className="flex items-center gap-1 bg-bg-surface2 rounded-lg p-1 ml-2">
          <button
            onClick={() => setTypeFilter('all')}
            className={`px-2.5 py-1 rounded-md text-[12px] font-medium transition ${
              typeFilter === 'all'
                ? 'bg-text text-white shadow'
                : 'text-text-2 hover:bg-white'
            }`}
          >
            Tümü
          </button>
          {TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`px-2.5 py-1 rounded-md text-[12px] font-medium transition ${
                typeFilter === t
                  ? 'bg-text text-white shadow'
                  : 'text-text-2 hover:bg-white'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative flex items-center ml-2">
          <Search className="w-3.5 h-3.5 absolute left-2.5 text-text-3" strokeWidth={2.2} />
          <input
            type="search"
            placeholder="Kurye / not ara…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8 pr-3 py-1.5 rounded-lg border border-border text-sm w-56 focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
          />
        </div>

        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
          {filtered.length} sonuç
        </span>
      </div>

      {/* ERROR */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-sm mb-3 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" strokeWidth={2.2} />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto text-red-600 hover:text-red-800">
            <X className="w-4 h-4" strokeWidth={2.4} />
          </button>
        </div>
      )}

      {/* LIST */}
      {filtered.length === 0 ? (
        <div className="bg-white border border-border rounded-2xl p-12 text-center">
          <Clock className="w-10 h-10 mx-auto text-text-3 mb-3" strokeWidth={1.5} />
          <div className="text-text-2 font-medium">Bu sekmede talep yok.</div>
          {statusTab === 'Beklemede' && (
            <div className="text-text-3 text-sm mt-1">
              Yeni bir talep oluşturmak için sağ üstteki butonu kullan.
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {filtered.map((r) => (
            <RequestCard
              key={r.id}
              r={r}
              busy={busyId === r.id}
              showActions={statusTab === 'Beklemede'}
              onApprove={() => handleDecide(r.id, 'Onaylandı')}
              onReject={() => handleDecide(r.id, 'Reddedildi')}
              onDelete={() => handleDelete(r.id)}
            />
          ))}
        </div>
      )}

      {/* MODAL */}
      {creating && (
        <NewRequestModal
          personnel={personnel}
          onClose={() => setCreating(false)}
          onCreated={() => {
            setCreating(false);
            router.refresh();
          }}
        />
      )}
    </>
  );
}

// ─── KPI Card ──────────────────────────────────────────────────────
function KpiCard({
  icon, accent, label, value, sub,
}: {
  icon: React.ReactNode;
  accent: 'brand' | 'success' | 'warn' | 'purple';
  label: string;
  value: string;
  sub: string;
}) {
  const ringMap: Record<string, string> = {
    brand: 'bg-gradient-to-b from-brand to-blue-400',
    success: 'bg-gradient-to-b from-green-500 to-emerald-300',
    warn: 'bg-gradient-to-b from-orange-500 to-amber-300',
    purple: 'bg-gradient-to-b from-purple-500 to-fuchsia-300',
  };
  const iconBgMap: Record<string, string> = {
    brand: 'bg-brand-soft text-brand',
    success: 'bg-green-100 text-green-700',
    warn: 'bg-orange-100 text-orange-700',
    purple: 'bg-purple-100 text-purple-700',
  };

  return (
    <div className="relative bg-white rounded-2xl px-5 py-4 shadow-sm border border-border overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition">
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${ringMap[accent]}`} />
      <div className="flex items-start justify-between mb-2">
        <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold">
          {label}
        </div>
        <div className={`w-7 h-7 rounded-lg ${iconBgMap[accent]} flex items-center justify-center`}>
          {icon}
        </div>
      </div>
      <div className="font-display text-[26px] font-bold tracking-tight leading-none num tabular-nums">
        {value}
      </div>
      <div className="text-[11px] text-text-3 mt-2 font-medium">{sub}</div>
    </div>
  );
}

// ─── Request Card ──────────────────────────────────────────────────
function RequestCard({
  r, busy, showActions, onApprove, onReject, onDelete,
}: {
  r: CourierRequest;
  busy: boolean;
  showActions: boolean;
  onApprove: () => void;
  onReject: () => void;
  onDelete: () => void;
}) {
  const meta = TYPE_META[r.request_type] ?? {
    Icon: User, bg: 'bg-slate-600', text: 'text-slate-700', soft: 'bg-slate-50 border-slate-200',
  };
  const initials = (r.personnel_name ?? '?')
    .split(' ').filter(Boolean).slice(0, 2)
    .map((w) => w[0]?.toUpperCase()).join('');
  const grad = AVATAR_GRADIENTS[(r.personnel_id ?? 0) % AVATAR_GRADIENTS.length];

  return (
    <div className={`relative bg-white border ${meta.soft.replace('bg-', 'border-').split(' ')[1] ?? 'border-border'} border-l-4 rounded-2xl p-4 shadow-sm hover:shadow-md transition`}>
      {/* Top row: avatar + type badge */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-[12px] flex-shrink-0 shadow ring-2 ring-white`}>
            {initials || '?'}
          </div>
          <div className="min-w-0 flex-1">
            <div className="font-semibold text-text text-[13.5px] truncate">
              {r.personnel_name ?? '—'}
            </div>
            <div className="text-[11px] text-text-3 truncate flex items-center gap-1.5 mt-0.5">
              <span className="font-mono">{r.person_code}</span>
              {r.rest_brand && (
                <>
                  <span>·</span>
                  <Building2 className="w-3 h-3" strokeWidth={2.2} />
                  <span className="truncate">{r.rest_brand}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <div className={`px-2 py-1 rounded-md text-[11px] font-bold inline-flex items-center gap-1 ${meta.soft} ${meta.text} flex-shrink-0`}>
          <meta.Icon className="w-3 h-3" strokeWidth={2.4} />
          {r.request_type}
        </div>
      </div>

      {/* Amount (avans) */}
      {r.request_type === 'Avans' && r.amount > 0 && (
        <div className="flex items-baseline gap-1.5 mb-2">
          <span className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold">Tutar:</span>
          <span className="font-display text-[20px] font-bold text-green-700 num tabular-nums">
            {tr(r.amount)} ₺
          </span>
        </div>
      )}

      {/* Motor Değişikliği detayları */}
      {r.request_type === 'Motor Değişikliği' && (r.vehicle_from || r.vehicle_to) && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-3 space-y-2">
          <div className="flex items-center gap-2 text-[12px]">
            <span className="px-2 py-0.5 rounded-md bg-white border border-orange-200 text-orange-800 font-semibold">
              {r.vehicle_from ?? '—'}
            </span>
            <span className="text-orange-600 font-bold">→</span>
            <span className="px-2 py-0.5 rounded-md bg-orange-600 text-white font-semibold">
              {r.vehicle_to ?? '—'}
            </span>
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11.5px]">
            {r.vehicle_reason && (
              <div className="text-orange-800">
                <strong className="text-[10px] uppercase tracking-wider opacity-75">Neden:</strong>{' '}
                <span className="font-semibold">{r.vehicle_reason}</span>
              </div>
            )}
            {r.plate && (
              <div className="text-orange-800">
                <strong className="text-[10px] uppercase tracking-wider opacity-75">Plaka:</strong>{' '}
                <span className="font-mono font-bold">{r.plate}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Muhasebe Değişimi detayları */}
      {r.request_type === 'Muhasebe Değişimi' && (r.accounting_from || r.accounting_to) && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-3">
          <div className="flex items-center gap-2 text-[12px]">
            <span className="px-2 py-0.5 rounded-md bg-white border border-purple-200 text-purple-800 font-semibold">
              {r.accounting_from ?? '—'}
            </span>
            <span className="text-purple-600 font-bold">→</span>
            <span className="px-2 py-0.5 rounded-md bg-purple-600 text-white font-semibold">
              {r.accounting_to ?? '—'}
            </span>
          </div>
        </div>
      )}

      {/* Reason */}
      {r.reason && (
        <div className="bg-cream-50 border border-border rounded-lg p-2.5 mb-3">
          <div className="text-[10px] uppercase tracking-wider text-text-3 font-bold mb-1">Açıklama</div>
          <div className="text-[12.5px] text-text-2 leading-snug">{r.reason}</div>
        </div>
      )}

      {/* Status footer */}
      <div className="flex items-center justify-between text-[11px] text-text-3">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3 h-3" strokeWidth={2.2} />
          <span>Talep: {relTime(r.requested_at)}</span>
        </div>
        {r.decided_at && (
          <div className="flex items-center gap-1.5">
            {r.status === 'Onaylandı' ? (
              <Check className="w-3 h-3 text-green-600" strokeWidth={2.4} />
            ) : (
              <XCircle className="w-3 h-3 text-red-600" strokeWidth={2.4} />
            )}
            <span>{r.status === 'Onaylandı' ? 'Onaylandı' : 'Reddedildi'}: {relTime(r.decided_at)}</span>
          </div>
        )}
      </div>

      {/* Decision notes (if any) */}
      {r.decision_notes && (
        <div className="text-[11px] text-text-3 mt-2 italic">
          Karar notu: {r.decision_notes}
        </div>
      )}

      {/* Action bar */}
      {showActions && (
        <div className="flex gap-2 mt-3 pt-3 border-t border-border">
          <button
            onClick={onApprove}
            disabled={busy}
            className="flex-1 px-3 py-2 rounded-lg bg-green-600 text-white text-[12.5px] font-semibold hover:bg-green-700 transition disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
          >
            <Check className="w-3.5 h-3.5" strokeWidth={2.4} /> Onayla
          </button>
          <button
            onClick={onReject}
            disabled={busy}
            className="flex-1 px-3 py-2 rounded-lg bg-white border border-red-200 text-red-700 text-[12.5px] font-semibold hover:bg-red-50 transition disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
          >
            <XCircle className="w-3.5 h-3.5" strokeWidth={2.4} /> Reddet
          </button>
          <button
            onClick={onDelete}
            disabled={busy}
            className="px-3 py-2 rounded-lg bg-white border border-border text-text-3 hover:text-red-600 hover:border-red-200 transition disabled:opacity-50"
            title="Sil"
          >
            <Trash2 className="w-3.5 h-3.5" strokeWidth={2.2} />
          </button>
        </div>
      )}

      {/* Karara verilmiş talepler için sil butonu (sağ üst) */}
      {!showActions && (
        <button
          onClick={onDelete}
          disabled={busy}
          className="absolute top-3 right-3 text-text-3 hover:text-red-600 transition opacity-30 hover:opacity-100"
          title="Sil"
        >
          <Trash2 className="w-3.5 h-3.5" strokeWidth={2.2} />
        </button>
      )}
    </div>
  );
}
