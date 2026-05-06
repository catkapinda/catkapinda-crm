'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  CheckCircle2, Clock, Loader2, Wallet, FileSpreadsheet,
  Hash, Banknote, Undo2, ShieldCheck,
} from 'lucide-react';

import {
  type PayrollSignature,
  markBordroPaid,
  unmarkBordroPaid,
} from '@/lib/api';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string): string {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('tr-TR', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('tr-TR', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

function relTime(iso: string | null): string {
  if (!iso) return '—';
  const t = new Date(iso).getTime();
  const diff = Date.now() - t;
  const min = Math.floor(diff / 60_000);
  if (min < 1) return 'az önce';
  if (min < 60) return `${min} dk önce`;
  const h = Math.floor(min / 60);
  if (h < 24) return `${h} sa önce`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} gün önce`;
  return formatDate(iso);
}

function m(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

type StatusKey = 'odenecek' | 'odendi' | 'imzalanmadi' | null;

export function HakedisOnayView({
  initialSignatures,
  periods,
  activePeriod,
  activeStatus,
}: {
  initialSignatures: PayrollSignature[];
  periods: string[];
  activePeriod: string;
  activeStatus: StatusKey;
}) {
  const [signatures, setSignatures] = useState<PayrollSignature[]>(initialSignatures);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const router = useRouter();

  const summary = useMemo(() => {
    let odenecek = 0;
    let odendi = 0;
    let toplamTutar = 0;
    for (const s of signatures) {
      if (s.paid_at) {
        odendi += 1;
        if (s.paid_amount) toplamTutar += s.paid_amount;
      } else {
        odenecek += 1;
      }
    }
    return { odenecek, odendi, toplamTutar };
  }, [signatures]);

  const odenecekList = signatures.filter((s) => !s.paid_at);
  const odendiList = signatures.filter((s) => s.paid_at);

  function buildHref(extra: Partial<{ ay: string | null; durum: string | null }>): string {
    const params = new URLSearchParams();
    const ay = extra.ay !== undefined ? extra.ay : activePeriod;
    const durum = extra.durum !== undefined ? extra.durum : activeStatus;
    if (ay) params.set('ay', ay);
    if (durum) params.set('durum', durum);
    const qs = params.toString();
    return `/hakedis-onaylari${qs ? `?${qs}` : ''}`;
  }

  async function handleMarkPaid(sig: PayrollSignature) {
    if (!confirm(
      `${sig.personnel_name ?? '—'} için ${formatPeriod(sig.period)} bordrosu` +
      ` ödendi olarak işaretlensin mi?`,
    )) return;
    setBusyId(sig.id);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const updated = await markBordroPaid(sig.personnel_id, sig.period);
      setSignatures((prev) => prev.map((s) => s.id === sig.id ? { ...s, ...updated } : s));
      setSuccessMsg(
        `${sig.personnel_name ?? '—'} · ${formatPeriod(sig.period)} ödendi olarak işaretlendi.`,
      );
      router.refresh();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'İşlem başarısız');
    } finally {
      setBusyId(null);
    }
  }

  async function handleUnmark(sig: PayrollSignature) {
    if (!confirm(
      `${sig.personnel_name ?? '—'} için ödendi işaretini geri al?`,
    )) return;
    setBusyId(sig.id);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      await unmarkBordroPaid(sig.personnel_id, sig.period);
      setSignatures((prev) => prev.map((s) => s.id === sig.id ? {
        ...s, paid_at: null, paid_by: null, paid_amount: null,
      } : s));
      setSuccessMsg(`${sig.personnel_name ?? '—'} ödendi işareti geri alındı.`);
      router.refresh();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'İşlem başarısız');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="text-[12px] text-text-3 mb-1">
        Finans · <span className="text-brand font-medium">Hakediş Onayları</span>
      </div>
      <h1 className="font-display text-[28px] font-bold tracking-tight">
        Hakediş Onayları
      </h1>
      <p className="text-text-3 text-[13.5px] mt-1 mb-6">
        Kuryeler bordrolarını imzalar · Ayın 15'inde ödendi olarak işaretle
      </p>

      {/* Stat kartları */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard
          label="ÖDENECEK"
          value={summary.odenecek}
          icon={<Clock className="w-5 h-5" />}
          tone="amber"
        />
        <StatCard
          label="ÖDENDİ"
          value={summary.odendi}
          icon={<CheckCircle2 className="w-5 h-5" />}
          tone="emerald"
        />
        <StatCard
          label="TOPLAM ÖDEME"
          value={summary.toplamTutar > 0 ? `₺${m(summary.toplamTutar)}` : '—'}
          icon={<Banknote className="w-5 h-5" />}
          tone="blue"
        />
      </div>

      {/* Filtreler */}
      <div className="flex flex-wrap items-center gap-2 mb-5">
        <span className="text-[12px] text-text-3 mr-2">Ay:</span>
        {periods.length === 0 && (
          <span className="text-[12px] text-text-3/70">Henüz ay yok</span>
        )}
        {periods.slice(0, 6).map((p) => (
          <Link
            key={p}
            href={buildHref({ ay: p })}
            className={[
              'px-3 py-1.5 rounded-lg text-[12.5px] font-medium border transition',
              activePeriod === p
                ? 'bg-brand text-white border-brand'
                : 'bg-bg-surface text-text-2 border-border hover:border-text/30',
            ].join(' ')}
          >
            {formatPeriod(p)}
          </Link>
        ))}
      </div>

      {errorMsg && (
        <div className="mb-4 px-4 py-2.5 rounded-xl text-[13px] font-medium border bg-red-50 border-red-200 text-red-700">
          {errorMsg}
        </div>
      )}

      {successMsg && (
        <div className="mb-4 flex items-start gap-2 px-4 py-3 rounded-xl text-[13px] font-medium border bg-emerald-50 border-emerald-200 text-emerald-800">
          <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" strokeWidth={2.4} />
          <div className="flex-1">{successMsg}</div>
          <button
            onClick={() => setSuccessMsg(null)}
            className="text-emerald-700/60 hover:text-emerald-900 transition flex-shrink-0"
            aria-label="Kapat"
          >
            ✕
          </button>
        </div>
      )}

      {/* Ödenecek liste */}
      {odenecekList.length > 0 && (
        <section className="mb-7">
          <h2 className="flex items-center gap-2 text-[13px] uppercase tracking-widest font-semibold text-amber-700 mb-3">
            <Clock className="w-3.5 h-3.5" />
            Hakediş İmzalayan Kuryeler · Ödenecek · {odenecekList.length}
          </h2>
          <div className="space-y-2.5">
            {odenecekList.map((s) => (
              <SignatureRow
                key={s.id}
                sig={s}
                busy={busyId === s.id}
                onMarkPaid={() => handleMarkPaid(s)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Ödendi liste (arşiv) */}
      {odendiList.length > 0 && (
        <section className="mb-6">
          <h2 className="flex items-center gap-2 text-[13px] uppercase tracking-widest font-semibold text-emerald-700 mb-3">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Ödendi · {odendiList.length}
          </h2>
          <div className="space-y-2.5">
            {odendiList.map((s) => (
              <SignatureRow
                key={s.id}
                sig={s}
                busy={busyId === s.id}
                onUnmark={() => handleUnmark(s)}
              />
            ))}
          </div>
        </section>
      )}

      {signatures.length === 0 && (
        <div className="bg-bg-surface border border-border rounded-2xl p-12 text-center text-text-3">
          <FileSpreadsheet className="w-10 h-10 mx-auto mb-3 text-text-3/60" strokeWidth={1.5} />
          <p className="text-[14px] font-medium text-text-2">Henüz imza yok</p>
          <p className="text-[12.5px] mt-1">
            {formatPeriod(activePeriod)} dönemi için imzalayan kurye yok. Puantaj
            onaylandığında kuryeler SMS alır, imzaladıkça burada görünür.
          </p>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label, value, icon, tone,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  tone: 'amber' | 'emerald' | 'blue';
}) {
  const palettes = {
    amber: {
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      iconBg: 'bg-amber-100 text-amber-700',
      label: 'text-amber-700',
    },
    emerald: {
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      iconBg: 'bg-emerald-100 text-emerald-700',
      label: 'text-emerald-700',
    },
    blue: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      iconBg: 'bg-blue-100 text-blue-700',
      label: 'text-blue-700',
    },
  } as const;
  const p = palettes[tone];
  return (
    <div className={`rounded-2xl border ${p.bg} ${p.border} p-5 flex items-center justify-between`}>
      <div>
        <div className={`text-[11px] font-semibold tracking-widest ${p.label}`}>{label}</div>
        <div className="text-[28px] font-display font-bold tabular-nums mt-1 text-text">
          {value}
        </div>
      </div>
      <div className={`w-10 h-10 rounded-xl ${p.iconBg} flex items-center justify-center`}>
        {icon}
      </div>
    </div>
  );
}

function SignatureRow({
  sig, busy, onMarkPaid, onUnmark,
}: {
  sig: PayrollSignature;
  busy: boolean;
  onMarkPaid?: () => void;
  onUnmark?: () => void;
}) {
  const isPaid = !!sig.paid_at;
  return (
    <div className={[
      'rounded-2xl border p-4 transition',
      isPaid ? 'bg-emerald-50/40 border-emerald-200/60' : 'bg-bg-surface border-border hover:border-text/20',
    ].join(' ')}>
      <div className="flex items-start gap-4">
        <div className={[
          'w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0',
          isPaid ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700',
        ].join(' ')}>
          {isPaid ? <CheckCircle2 className="w-5 h-5" /> : <Wallet className="w-5 h-5" />}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h3 className="font-semibold text-[15px] text-text">
              {sig.personnel_name ?? '—'}
            </h3>
            {sig.person_code && (
              <span className="text-[11px] font-mono text-text-3 bg-bg-surface2 px-1.5 py-0.5 rounded">
                {sig.person_code}
              </span>
            )}
            {sig.role && (
              <span className="text-[11px] text-text-3">{sig.role}</span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-[12.5px] text-text-3">
            <span className="inline-flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              İmza: {relTime(sig.signed_at)}
            </span>
            {sig.iban && (
              <span className="inline-flex items-center gap-1 font-mono">
                <Hash className="w-3.5 h-3.5" />
                {sig.iban}
              </span>
            )}
            {isPaid && (
              <span className="inline-flex items-center gap-1 text-emerald-700 font-medium">
                <Banknote className="w-3.5 h-3.5" />
                Ödendi: {formatDateTime(sig.paid_at)}
                {sig.paid_amount ? ` · ₺${m(sig.paid_amount)}` : ''}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-2 flex-shrink-0">
          {!isPaid && onMarkPaid && (
            <button
              onClick={onMarkPaid}
              disabled={busy}
              className="px-4 py-2 rounded-xl bg-emerald-600 text-white text-[13px] font-semibold hover:bg-emerald-700 transition disabled:opacity-50 flex items-center gap-1.5"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Banknote className="w-4 h-4" />}
              Ödendi işaretle
            </button>
          )}
          {isPaid && onUnmark && (
            <button
              onClick={onUnmark}
              disabled={busy}
              className="px-3 py-1.5 rounded-lg bg-bg-surface border border-border text-text-2 text-[12px] font-medium hover:bg-bg-surface2 transition disabled:opacity-50 flex items-center gap-1.5"
              title="Yanlış işaretlendiyse"
            >
              {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Undo2 className="w-3.5 h-3.5" />}
              Geri al
            </button>
          )}
          <Link
            href={`/bordro/${sig.personnel_id}?ay=${sig.period}`}
            className="px-3 py-1.5 rounded-lg bg-bg-surface border border-border text-text-2 text-[12px] font-medium hover:bg-bg-surface2 transition flex items-center gap-1.5"
          >
            Bordroyu görüntüle
          </Link>
        </div>
      </div>
    </div>
  );
}
