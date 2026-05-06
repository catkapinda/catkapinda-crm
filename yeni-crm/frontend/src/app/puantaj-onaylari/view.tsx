'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  CheckCircle2, XCircle, Clock, Loader2, ShieldCheck, ShieldX,
  Building2, Hash, Package, Timer, FileSpreadsheet, ArrowRight,
} from 'lucide-react';

import {
  type PuantajApproval,
  decidePuantajApproval,
} from '@/lib/api';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string | null): string {
  if (!p) return '—';
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
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
  return new Date(iso).toLocaleDateString('tr-TR');
}

function tr(value: number, digits = 0): string {
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

const PRICING_LABELS: Record<string, string> = {
  hourly_only: 'Saatlik',
  hourly_plus_package: 'Saat + Paket',
  threshold_package: 'Eşik + Paket',
  fixed_monthly: 'Sabit Aylık',
};

export function PuantajOnayView({
  initialApprovals,
  periods,
  activePeriod,
  activeStatus,
}: {
  initialApprovals: PuantajApproval[];
  periods: string[];
  activePeriod: string | null;
  activeStatus: 'pending' | 'approved' | 'rejected' | null;
}) {
  const [approvals, setApprovals] = useState<PuantajApproval[]>(initialApprovals);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [rejectFor, setRejectFor] = useState<PuantajApproval | null>(null);
  const [rejectNotes, setRejectNotes] = useState('');
  const router = useRouter();

  const summary = useMemo(() => {
    const s = { pending: 0, approved: 0, rejected: 0 };
    for (const a of initialApprovals) {
      if (a.status === 'pending') s.pending += 1;
      else if (a.status === 'approved') s.approved += 1;
      else if (a.status === 'rejected') s.rejected += 1;
    }
    return s;
  }, [initialApprovals]);

  async function handleDecide(
    approval: PuantajApproval,
    status: 'approved' | 'rejected',
    notes?: string,
  ) {
    setBusyId(approval.id);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const updated = await decidePuantajApproval(
        approval.id,
        status,
        undefined,
        notes,
      );
      setApprovals((prev) =>
        prev.map((a) => (a.id === approval.id ? updated : a)),
      );
      // Onay sonrası SMS bildirim sonucu — backend response.notification içinde
      if (status === 'approved') {
        const n = updated.notification;
        const restaurant = `${approval.rest_brand ?? '—'}${
          approval.rest_branch ? ' · ' + approval.rest_branch : ''
        }`;
        const period = formatPeriod(approval.period);
        if (n?.error) {
          setSuccessMsg(
            `${restaurant} · ${period} onaylandı, fakat SMS bildiriminde sorun oluştu (${n.error}). Backend log'a bakınız.`,
          );
        } else if (n) {
          const parts: string[] = [];
          if (n.sent && n.sent > 0) parts.push(`${n.sent} kuryeye SMS gönderildi`);
          if (n.skipped_already_sent && n.skipped_already_sent > 0)
            parts.push(`${n.skipped_already_sent} kurye için bu ay zaten SMS atılmıştı`);
          if (n.not_in_allowlist && n.not_in_allowlist > 0)
            parts.push(`${n.not_in_allowlist} kurye allowlist dışı (test modu)`);
          if (n.no_phone && n.no_phone > 0)
            parts.push(`${n.no_phone} kuryenin telefonu kayıtlı değil`);
          if (n.failed && n.failed > 0) parts.push(`${n.failed} kuryede SMS hatası`);
          const detail = parts.length ? ` · ${parts.join(' · ')}` : '';
          setSuccessMsg(`${restaurant} · ${period} onaylandı${detail}.`);
        } else {
          setSuccessMsg(`${restaurant} · ${period} onaylandı.`);
        }
      } else {
        // rejected
        setSuccessMsg(
          `${approval.rest_brand ?? ''}${
            approval.rest_branch ? ' · ' + approval.rest_branch : ''
          } · ${formatPeriod(approval.period)} reddedildi.`,
        );
      }
      router.refresh();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'İşlem başarısız');
    } finally {
      setBusyId(null);
    }
  }

  function buildHref(extra: Partial<{ ay: string | null; durum: string | null }>): string {
    const params = new URLSearchParams();
    const ay = extra.ay !== undefined ? extra.ay : activePeriod;
    const durum = extra.durum !== undefined ? extra.durum : activeStatus;
    if (ay) params.set('ay', ay);
    if (durum) params.set('durum', durum);
    const qs = params.toString();
    return `/puantaj-onaylari${qs ? `?${qs}` : ''}`;
  }

  const pending = approvals.filter((a) => a.status === 'pending');
  const decided = approvals.filter((a) => a.status !== 'pending');

  return (
    <>
      {/* Header */}
      <header className="mb-6">
        <div className="text-[13px] text-text-3 font-medium mb-1.5">
          Operasyon · <span className="text-brand">Puantaj Onayları</span>
        </div>
        <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
          Puantaj Onayları
        </h1>
        <div className="text-text-3 text-sm mt-1 font-medium">
          Operasyon ekibi onaya gönderdi · admin kontrol edip bordroya açar
        </div>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-5">
        <StatCard
          label="Bekleyen"
          value={summary.pending}
          icon={Clock}
          accent="warn"
        />
        <StatCard
          label="Onaylandı"
          value={summary.approved}
          icon={ShieldCheck}
          accent="success"
        />
        <StatCard
          label="Reddedildi"
          value={summary.rejected}
          icon={ShieldX}
          accent="danger"
        />
      </div>

      {/* Filters */}
      <div className="flex gap-2 items-center mb-4 flex-wrap">
        {/* Period nav */}
        <div className="flex items-center gap-1 bg-bg-surface border border-border rounded-xl p-1 shadow-sm">
          <Link
            href={buildHref({ ay: null })}
            className={`px-3 py-1.5 rounded-lg text-[12.5px] font-medium transition ${
              !activePeriod
                ? 'bg-brand text-white shadow-sm'
                : 'text-text-2 hover:bg-bg-surface2'
            }`}
          >
            Tüm aylar
          </Link>
          {periods.slice(0, 4).map((p) => {
            const isActive = p === activePeriod;
            return (
              <Link
                key={p}
                href={buildHref({ ay: p })}
                className={`px-3 py-1.5 rounded-lg text-[12.5px] font-medium transition ${
                  isActive
                    ? 'bg-brand text-white shadow-sm'
                    : 'text-text-2 hover:bg-bg-surface2'
                }`}
              >
                {formatPeriod(p)}
              </Link>
            );
          })}
        </div>
        <div className="flex items-center gap-1 bg-bg-surface border border-border rounded-xl p-1 shadow-sm">
          {(
            [
              { k: null, label: 'Hepsi' },
              { k: 'pending', label: 'Bekleyen' },
              { k: 'approved', label: 'Onaylı' },
              { k: 'rejected', label: 'Reddedilen' },
            ] as const
          ).map((s) => {
            const active = activeStatus === s.k || (!activeStatus && s.k === null);
            return (
              <Link
                key={s.label}
                href={buildHref({ durum: s.k })}
                className={`px-3 py-1.5 rounded-lg text-[12.5px] font-medium transition ${
                  active
                    ? 'bg-brand text-white shadow-sm'
                    : 'text-text-2 hover:bg-bg-surface2'
                }`}
              >
                {s.label}
              </Link>
            );
          })}
        </div>
        <span className="text-[11px] text-text-3 font-semibold uppercase tracking-wider ml-auto">
          {approvals.length} kayıt
        </span>
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
            <XCircle className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Pending list */}
      {pending.length > 0 && (
        <section className="mb-7">
          <h2 className="text-[12px] font-bold text-text-3 tracking-[0.1em] uppercase mb-3 flex items-center gap-2">
            <Clock className="w-3.5 h-3.5 text-yellow-600" />
            Bekleyen Onaylar · {pending.length}
          </h2>
          <div className="grid gap-3">
            {pending.map((a) => (
              <ApprovalCard
                key={a.id}
                approval={a}
                busy={busyId === a.id}
                onApprove={() => handleDecide(a, 'approved')}
                onReject={() => {
                  setRejectFor(a);
                  setRejectNotes('');
                }}
              />
            ))}
          </div>
        </section>
      )}

      {/* Decided list */}
      {decided.length > 0 && (
        <section>
          <h2 className="text-[12px] font-bold text-text-3 tracking-[0.1em] uppercase mb-3">
            Karar Verildi · {decided.length}
          </h2>
          <div className="grid gap-3">
            {decided.map((a) => (
              <ApprovalCard
                key={a.id}
                approval={a}
                busy={busyId === a.id}
                onApprove={() => handleDecide(a, 'approved')}
                onReject={() => {
                  setRejectFor(a);
                  setRejectNotes('');
                }}
              />
            ))}
          </div>
        </section>
      )}

      {approvals.length === 0 && (
        <div className="bg-bg-surface border border-border rounded-2xl p-12 text-center text-text-3">
          <FileSpreadsheet className="w-10 h-10 mx-auto mb-3 text-text-3/60" strokeWidth={1.5} />
          <p className="text-[14px] font-medium text-text-2">Henüz kayıt yok</p>
          <p className="text-[12.5px] mt-1">
            Operasyon ekibi puantajı doldurup &quot;Onaya Gönder&quot; dediğinde burada görünecek.
          </p>
        </div>
      )}

      {/* Reject modal */}
      {rejectFor && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4"
          onClick={() => setRejectFor(null)}
        >
          <div
            className="bg-bg-surface rounded-2xl shadow-2xl border border-border max-w-md w-full p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-display text-[18px] font-semibold mb-1">
              Reddet
            </h3>
            <p className="text-[13px] text-text-3 mb-4">
              {rejectFor.rest_brand} {rejectFor.rest_branch ? `· ${rejectFor.rest_branch}` : ''} · {formatPeriod(rejectFor.period)}
            </p>
            <label className="block text-[12px] font-semibold text-text-2 mb-1.5">
              Red gerekçesi (operasyon ekibi görür)
            </label>
            <textarea
              value={rejectNotes}
              onChange={(e) => setRejectNotes(e.target.value)}
              rows={4}
              placeholder="Örn: Berk Can'ın 12 Mart girişi eksik, kontrol edip tekrar gönderin."
              className="w-full px-3 py-2 rounded-lg border border-border text-sm bg-bg-surface focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
            />
            <div className="flex gap-2 justify-end mt-4">
              <button
                onClick={() => setRejectFor(null)}
                className="px-4 py-2 rounded-lg border border-border text-text-2 text-[13px] font-medium hover:bg-bg-surface2 transition"
              >
                Vazgeç
              </button>
              <button
                onClick={async () => {
                  const a = rejectFor;
                  setRejectFor(null);
                  await handleDecide(a, 'rejected', rejectNotes.trim() || undefined);
                }}
                disabled={busyId === rejectFor.id}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-[13px] font-semibold hover:bg-red-700 transition disabled:opacity-50 flex items-center gap-1.5"
              >
                {busyId === rejectFor.id ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <XCircle className="w-4 h-4" />
                )}
                Reddi gönder
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ApprovalCard({
  approval,
  busy,
  onApprove,
  onReject,
}: {
  approval: PuantajApproval;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  const isPending = approval.status === 'pending';
  const isApproved = approval.status === 'approved';
  const isRejected = approval.status === 'rejected';

  return (
    <div
      className={`bg-bg-surface border rounded-2xl p-4 shadow-sm transition ${
        isPending
          ? 'border-yellow-200'
          : isApproved
          ? 'border-green-200'
          : 'border-red-200'
      }`}
    >
      <div className="flex items-start gap-4">
        {/* Sol: restoran kimlik */}
        <div className="flex-shrink-0">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-brand to-brand-dark text-white flex items-center justify-center shadow-sm">
            <Building2 className="w-5 h-5" strokeWidth={2.2} />
          </div>
        </div>

        {/* Orta: detay */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <h3 className="font-semibold text-[15px] text-text">
              {approval.rest_brand ?? '— marka yok —'}
              {approval.rest_branch ? (
                <span className="font-normal text-text-2"> · {approval.rest_branch}</span>
              ) : null}
            </h3>
            <span className="px-2 py-0.5 rounded-full text-[10.5px] font-semibold bg-bg-surface2 text-text-3 uppercase tracking-wider">
              {formatPeriod(approval.period)}
            </span>
            {approval.pricing_model && (
              <span className="px-2 py-0.5 rounded-full text-[10.5px] font-semibold bg-brand-soft/30 text-brand-dark">
                {PRICING_LABELS[approval.pricing_model] ?? approval.pricing_model}
              </span>
            )}
            <StatusPill status={approval.status} />
          </div>
          <div className="text-[12px] text-text-3 mb-2.5">
            {approval.submitted_by ? (
              <>
                <strong className="text-text-2">{approval.submitted_by}</strong>{' '}
                gönderdi · {relTime(approval.submitted_at)}
              </>
            ) : (
              <>Gönderildi · {relTime(approval.submitted_at)}</>
            )}
            {approval.decided_at && (
              <>
                {' '}· {isApproved ? 'Onay' : 'Red'}: {relTime(approval.decided_at)}
                {approval.decided_by ? ` (${approval.decided_by})` : ''}
              </>
            )}
          </div>

          {/* Snapshot rakamlar */}
          <div className="grid grid-cols-3 gap-2 mb-2">
            <Metric icon={Hash} label="Kayıt" value={tr(approval.entry_count)} />
            <Metric icon={Timer} label="Saat" value={tr(Math.round(approval.total_hours))} />
            <Metric icon={Package} label="Paket" value={tr(approval.total_packages)} />
          </div>

          {approval.decision_notes && (
            <div className="mt-2 px-3 py-2 rounded-lg bg-red-50 border border-red-100 text-[12.5px] text-red-700">
              <strong>Red notu:</strong> {approval.decision_notes}
            </div>
          )}

          <div className="flex items-center gap-2 mt-3 flex-wrap">
            <Link
              href={`/puantaj?ay=${approval.period}`}
              className="px-3 py-1.5 rounded-lg border border-border text-text-2 text-[12px] font-medium hover:border-text/30 transition flex items-center gap-1.5"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" /> Puantajı görüntüle
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>

        {/* Sağ: aksiyonlar */}
        {isPending && (
          <div className="flex-shrink-0 flex flex-col gap-2 min-w-[140px]">
            <button
              onClick={onApprove}
              disabled={busy}
              className="px-4 py-2 rounded-lg bg-green-600 text-white text-[13px] font-semibold shadow-sm hover:bg-green-700 transition disabled:opacity-50 flex items-center gap-1.5 justify-center"
            >
              {busy ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4" />
              )}
              Onayla
            </button>
            <button
              onClick={onReject}
              disabled={busy}
              className="px-4 py-2 rounded-lg border border-red-200 text-red-700 text-[13px] font-semibold hover:bg-red-50 transition disabled:opacity-50 flex items-center gap-1.5 justify-center"
            >
              <XCircle className="w-4 h-4" /> Reddet
            </button>
          </div>
        )}

        {!isPending && (
          <div className="flex-shrink-0 flex flex-col gap-2 min-w-[140px]">
            <button
              onClick={onApprove}
              disabled={busy || isApproved}
              className="px-3 py-1.5 rounded-lg border border-border text-text-2 text-[12px] font-medium hover:bg-bg-surface2 transition disabled:opacity-50"
              title="Yeniden onayla"
            >
              {isApproved ? '✓ Onaylandı' : 'Onayla'}
            </button>
            {!isRejected && (
              <button
                onClick={onReject}
                disabled={busy}
                className="px-3 py-1.5 rounded-lg border border-border text-text-2 text-[12px] font-medium hover:bg-bg-surface2 transition disabled:opacity-50"
              >
                Reddet
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: 'pending' | 'approved' | 'rejected' }) {
  const map = {
    pending: { label: 'Bekliyor', cls: 'bg-yellow-100 text-yellow-800', dot: 'bg-yellow-500' },
    approved: { label: 'Onaylandı', cls: 'bg-green-100 text-green-800', dot: 'bg-green-500' },
    rejected: { label: 'Reddedildi', cls: 'bg-red-100 text-red-800', dot: 'bg-red-500' },
  } as const;
  const s = map[status];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10.5px] font-semibold ${s.cls}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Hash;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-surface2 border border-border">
      <Icon className="w-3.5 h-3.5 text-text-3" strokeWidth={2.2} />
      <div className="leading-tight">
        <div className="text-[10.5px] text-text-3 uppercase tracking-wider font-semibold">
          {label}
        </div>
        <div className="text-[14px] font-semibold tabular-nums text-text">
          {value}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: number;
  icon: typeof Clock;
  accent: 'warn' | 'success' | 'danger';
}) {
  const accentMap = {
    warn: { bg: 'bg-yellow-100', text: 'text-yellow-700', border: 'border-yellow-200' },
    success: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-200' },
    danger: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
  };
  const a = accentMap[accent];
  return (
    <div className={`bg-bg-surface border ${a.border} rounded-2xl p-4 shadow-sm`}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider font-semibold text-text-3">
            {label}
          </div>
          <div className="font-display text-[28px] font-bold tabular-nums leading-tight mt-1">
            {value}
          </div>
        </div>
        <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${a.bg}`}>
          <Icon className={`w-5 h-5 ${a.text}`} strokeWidth={2.2} />
        </div>
      </div>
    </div>
  );
}
