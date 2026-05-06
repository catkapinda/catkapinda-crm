'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, Banknote, Check, CheckCircle2, Clock, Search,
  Trash2, X, XCircle,
} from 'lucide-react';

import {
  type CourierRequest,
  type Personnel,
  decideCourierRequest,
  deleteCourierRequest,
} from '@/lib/api';

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

const AVATAR_GRADIENTS = [
  'from-emerald-700 to-emerald-500',
  'from-green-700 to-green-500',
  'from-teal-700 to-teal-500',
  'from-emerald-800 to-green-600',
];

function avatarFor(seed: string): string {
  const i = Math.abs(seed.split('').reduce((a, c) => a + c.charCodeAt(0), 0)) % AVATAR_GRADIENTS.length;
  return AVATAR_GRADIENTS[i];
}

export function AvansTalepleriView({
  requests,
  personnel: _personnel,
}: {
  requests: CourierRequest[];
  personnel: Personnel[];
}) {
  const router = useRouter();
  const [statusTab, setStatusTab] = useState<StatusKey>('Beklemede');
  const [search, setSearch] = useState('');
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const counts = useMemo(() => {
    const c = { Beklemede: 0, Onaylandı: 0, Reddedildi: 0, total: requests.length };
    for (const r of requests) {
      if (r.status in c) c[r.status as StatusKey]++;
    }
    return c;
  }, [requests]);

  const totals = useMemo(() => {
    let bekliyor = 0;
    let onayli = 0;
    for (const r of requests) {
      if (r.status === 'Beklemede') bekliyor += r.amount || 0;
      else if (r.status === 'Onaylandı') onayli += r.amount || 0;
    }
    return { bekliyor, onayli };
  }, [requests]);

  const filtered = useMemo(() => {
    const q = search.trim().toLocaleLowerCase('tr-TR');
    return requests.filter((r) => {
      if (r.status !== statusTab) return false;
      if (q) {
        const hay = `${r.personnel_name ?? ''} ${r.person_code ?? ''} ${r.reason ?? ''}`
          .toLocaleLowerCase('tr-TR');
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [requests, statusTab, search]);

  async function handleDecide(id: number, status: 'Onaylandı' | 'Reddedildi') {
    if (busyId != null) return;
    if (!confirm(
      `Bu avans talebini ${status === 'Onaylandı' ? 'ONAYLAMAK' : 'REDDETMEK'} istediğine emin misin?`,
    )) return;
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
    if (!confirm('Bu avans talebi tamamen silinecek. Devam edilsin mi?')) return;
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
            Operasyon · <span className="text-emerald-700 font-semibold">Avans Talepleri</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
            Avans Talepleri
          </h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            Kuryelerin /kurye/avans üzerinden gönderdiği avans talepleri ·
            {' '}{counts.Beklemede} bekleyen · {counts.Onaylandı} onaylanan · {counts.Reddedildi} reddedilen
          </div>
        </div>
      </header>

      {/* HERO STRIP — 3 KPI */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <KpiCard
          icon={<Clock className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="amber"
          label="Bekleyen Talep"
          value={String(counts.Beklemede)}
          sub={`₺${tr(totals.bekliyor)} toplam`}
        />
        <KpiCard
          icon={<CheckCircle2 className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="emerald"
          label="Onaylandı"
          value={String(counts.Onaylandı)}
          sub={`₺${tr(totals.onayli)} ödenecek`}
        />
        <KpiCard
          icon={<XCircle className="w-3.5 h-3.5" strokeWidth={2.2} />}
          accent="rose"
          label="Reddedildi"
          value={String(counts.Reddedildi)}
          sub="bu ay"
        />
      </div>

      {/* STATUS TABS + SEARCH */}
      <div className="bg-white border border-border rounded-2xl p-3 shadow-sm mb-4 flex flex-wrap items-center gap-2 sticky top-2 z-10 backdrop-blur-sm">
        <div className="flex items-center gap-1 bg-bg-surface2 rounded-lg p-1">
          {(['Beklemede', 'Onaylandı', 'Reddedildi'] as StatusKey[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatusTab(s)}
              className={[
                'px-3 py-1.5 rounded-md text-[13px] font-semibold transition',
                statusTab === s
                  ? 'bg-white text-text shadow-sm'
                  : 'text-text-3 hover:text-text',
              ].join(' ')}
            >
              {s} <span className="text-text-3/70 ml-1">({counts[s]})</span>
            </button>
          ))}
        </div>

        <div className="flex-1 min-w-[200px] relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Kurye / kod / sebep..."
            className="w-full pl-10 pr-3 py-2 rounded-lg border border-border text-[13px] bg-bg-surface focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
          />
        </div>

        <span className="text-[12px] text-text-3 font-medium ml-auto">
          {filtered.length} sonuç
        </span>
      </div>

      {error && (
        <div className="mb-4 px-4 py-2.5 rounded-xl text-[13px] font-medium border bg-red-50 border-red-200 text-red-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* LIST */}
      {filtered.length === 0 ? (
        <div className="bg-bg-surface border border-border rounded-2xl p-12 text-center text-text-3">
          <Banknote className="w-10 h-10 mx-auto mb-3 text-text-3/60" strokeWidth={1.5} />
          <p className="text-[14px] font-medium text-text-2">
            {statusTab === 'Beklemede'
              ? 'Bekleyen avans talebi yok'
              : statusTab === 'Onaylandı'
              ? 'Henüz onaylanan avans yok'
              : 'Henüz reddedilen avans yok'}
          </p>
          <p className="text-[12.5px] mt-1">
            Kuryeler kurye.crmcatkapinda.com/kurye/avans üzerinden talep gönderdiğinde burada listelenecek.
          </p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {filtered.map((r) => (
            <AvansRow
              key={r.id}
              r={r}
              busy={busyId === r.id}
              onApprove={() => handleDecide(r.id, 'Onaylandı')}
              onReject={() => handleDecide(r.id, 'Reddedildi')}
              onDelete={() => handleDelete(r.id)}
            />
          ))}
        </div>
      )}
    </>
  );
}

function AvansRow({
  r, busy, onApprove, onReject, onDelete,
}: {
  r: CourierRequest;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
  onDelete: () => void;
}) {
  const isPending = r.status === 'Beklemede';
  const initials = (r.personnel_name ?? '?')
    .split(' ').filter(Boolean).slice(0, 2)
    .map((w) => w[0]?.toUpperCase()).join('');

  return (
    <div className="rounded-2xl border border-border bg-bg-surface p-4 hover:border-text/20 transition">
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div
          className={[
            'w-11 h-11 rounded-xl bg-gradient-to-br',
            avatarFor(r.personnel_name ?? ''),
            'text-white font-bold flex items-center justify-center flex-shrink-0',
          ].join(' ')}
        >
          {initials || '?'}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h3 className="font-semibold text-[15px] text-text">
              {r.personnel_name ?? '—'}
            </h3>
            {r.person_code && (
              <span className="text-[11px] font-mono text-text-3 bg-bg-surface2 px-1.5 py-0.5 rounded">
                {r.person_code}
              </span>
            )}
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <Banknote className="w-3 h-3" />
              ₺{tr(r.amount)}
            </span>
          </div>

          {r.reason && (
            <p className="text-[13px] text-text-2 mt-1.5 leading-snug">
              {r.reason}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-[12px] text-text-3">
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {relTime(r.created_at)}
            </span>
            {r.decided_at && (
              <span className="inline-flex items-center gap-1">
                Karar: {relTime(r.decided_at)}
                {r.decided_by ? ` · ${r.decided_by}` : ''}
              </span>
            )}
            {r.decision_notes && (
              <span className="italic text-text-3/80">
                &quot;{r.decision_notes}&quot;
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 flex-shrink-0">
          {isPending ? (
            <>
              <button
                onClick={onApprove}
                disabled={busy}
                className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-[13px] font-semibold hover:bg-emerald-700 transition disabled:opacity-50 flex items-center gap-1.5"
              >
                <Check className="w-4 h-4" /> Onayla
              </button>
              <button
                onClick={onReject}
                disabled={busy}
                className="px-3 py-1.5 rounded-lg border border-border text-text-2 text-[12px] font-medium hover:bg-bg-surface2 transition disabled:opacity-50 flex items-center gap-1.5"
              >
                <X className="w-3.5 h-3.5" /> Reddet
              </button>
            </>
          ) : (
            <button
              onClick={onDelete}
              disabled={busy}
              className="px-3 py-1.5 rounded-lg border border-border text-text-3 text-[12px] font-medium hover:bg-bg-surface2 hover:text-red-600 transition disabled:opacity-50 flex items-center gap-1.5"
              title="Kaydı sil"
            >
              <Trash2 className="w-3.5 h-3.5" /> Sil
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  icon, accent, label, value, sub,
}: {
  icon: React.ReactNode;
  accent: 'amber' | 'emerald' | 'rose';
  label: string;
  value: string;
  sub?: string;
}) {
  const palettes = {
    amber: { bg: 'bg-amber-50', border: 'border-amber-200', icon: 'bg-amber-100 text-amber-700', label: 'text-amber-700' },
    emerald: { bg: 'bg-emerald-50', border: 'border-emerald-200', icon: 'bg-emerald-100 text-emerald-700', label: 'text-emerald-700' },
    rose: { bg: 'bg-rose-50', border: 'border-rose-200', icon: 'bg-rose-100 text-rose-700', label: 'text-rose-700' },
  } as const;
  const p = palettes[accent];
  return (
    <div className={`rounded-2xl border ${p.bg} ${p.border} p-4`}>
      <div className="flex items-center justify-between mb-2">
        <div className={`text-[10.5px] font-bold tracking-widest ${p.label}`}>
          {label.toUpperCase()}
        </div>
        <div className={`w-7 h-7 rounded-lg ${p.icon} flex items-center justify-center`}>
          {icon}
        </div>
      </div>
      <div className="text-[28px] font-display font-bold tabular-nums text-text">
        {value}
      </div>
      {sub && (
        <div className="text-[11.5px] text-text-3 mt-0.5 font-medium">{sub}</div>
      )}
    </div>
  );
}
