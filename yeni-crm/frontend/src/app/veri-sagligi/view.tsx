'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertTriangle, Calendar, Check, CheckCircle2, ChevronDown,
  ChevronRight, HeartPulse, RefreshCw, XCircle,
} from 'lucide-react';

import type { DataHealthCheck, DataHealthResponse } from '@/lib/api';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];
const MIN_PERIOD = '2026-03';

function formatPeriod(p: string): string {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}
function recentPeriodOptions(max = 6) {
  const now = new Date();
  const out: { value: string; label: string }[] = [];
  for (let i = 0; i < max; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const v = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    out.push({ value: v, label: `${TR_MONTHS[d.getMonth()]} ${d.getFullYear()}` });
    if (v === MIN_PERIOD) break;
  }
  return out;
}

const STATUS_STYLE: Record<string, { bg: string; border: string; text: string; icon: typeof Check; label: string }> = {
  green: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', icon: CheckCircle2, label: 'OK' },
  yellow: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', icon: AlertTriangle, label: 'Uyarı' },
  red: { bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-700', icon: XCircle, label: 'Sorun' },
};

export function VeriSagligiView({
  data, period,
}: {
  data: DataHealthResponse;
  period: string;
}) {
  const router = useRouter();
  const periodOptions = useMemo(() => recentPeriodOptions(6), []);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  function changePeriod(next: string) {
    setPickerOpen(false);
    if (next === period) return;
    router.push(`/veri-sagligi?period=${next}`);
  }
  function refresh() {
    setRefreshing(true);
    router.refresh();
    setTimeout(() => setRefreshing(false), 800);
  }

  const overallStyle = STATUS_STYLE[data.summary.overall_status];
  const OverallIcon = overallStyle.icon;

  return (
    <div className="flex flex-col gap-6">
      {/* HERO */}
      <section className="relative z-20 rounded-3xl shadow-lg">
        <div className="absolute inset-0 overflow-hidden rounded-3xl pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-br from-brand-dark via-brand to-blue-600" />
          <div
            className="absolute inset-0 opacity-30 mix-blend-overlay"
            style={{ backgroundImage: 'radial-gradient(circle at 20% 20%, rgba(255,255,255,.4) 0%, transparent 40%), radial-gradient(circle at 80% 70%, rgba(255,200,100,.3) 0%, transparent 50%)' }}
          />
          <div
            className="absolute inset-0 opacity-[0.07]"
            style={{ backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)', backgroundSize: '24px 24px' }}
          />
        </div>
        <div className="relative px-7 py-7 text-white flex items-start justify-between gap-6 flex-wrap">
          <div>
            <div className="text-[11px] font-medium tracking-[0.2em] uppercase text-white/70 mb-2 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-yellow-300 animate-pulse" />
              Sistem · Veri Sağlığı
            </div>
            <h1 className="text-4xl font-bold mb-1 flex items-center gap-3">
              <HeartPulse className="w-8 h-8" />
              Veri Sağlığı
            </h1>
            <div className="text-white/80">
              {formatPeriod(period)} · {data.summary.total_checks} kontrol ·{' '}
              <span className="text-emerald-200 font-semibold">{data.summary.green} OK</span>
              {data.summary.yellow > 0 && (
                <> · <span className="text-amber-200 font-semibold">{data.summary.yellow} uyarı</span></>
              )}
              {data.summary.red > 0 && (
                <> · <span className="text-rose-200 font-semibold">{data.summary.red} sorun</span></>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refresh}
              disabled={refreshing}
              className="px-3.5 py-2 rounded-lg bg-white/15 backdrop-blur-sm border border-white/25 text-white text-xs font-semibold hover:bg-white/25 transition inline-flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} strokeWidth={2.4} />
              Yenile
            </button>
            <div className="relative">
              <button
                onClick={() => setPickerOpen((v) => !v)}
                className="px-3.5 py-2 rounded-lg bg-white/15 backdrop-blur-sm border border-white/25 text-white text-xs font-semibold hover:bg-white/25 transition inline-flex items-center gap-2"
              >
                <Calendar className="w-3.5 h-3.5" strokeWidth={2.2} />
                <span>{formatPeriod(period)}</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${pickerOpen ? 'rotate-180' : ''}`} strokeWidth={2.4} />
              </button>
              {pickerOpen && (
                <>
                  <div className="fixed inset-0 z-30" onClick={() => setPickerOpen(false)} />
                  <div className="absolute right-0 mt-1.5 z-40 w-52 bg-white border border-border rounded-xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
                    <div className="px-3 py-2 text-[10px] uppercase tracking-wider font-bold text-text-3 border-b border-border/60">
                      Dönem seç
                    </div>
                    {periodOptions.map((opt) => {
                      const active = opt.value === period;
                      return (
                        <button
                          key={opt.value}
                          onClick={() => changePeriod(opt.value)}
                          className={`w-full text-left px-3 py-2 text-xs font-semibold flex items-center justify-between transition ${
                            active ? 'bg-brand-soft text-brand' : 'text-text-2 hover:bg-bg-surface2'
                          }`}
                        >
                          <span>{opt.label}</span>
                          {active && <Check className="w-3.5 h-3.5" strokeWidth={3} />}
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Genel durum kart */}
      <div className={`rounded-2xl border ${overallStyle.bg} ${overallStyle.border} p-4 flex items-center gap-3`}>
        <OverallIcon className={`w-8 h-8 ${overallStyle.text}`} strokeWidth={2.2} />
        <div>
          <div className={`text-sm font-bold ${overallStyle.text} uppercase tracking-wider`}>
            Genel durum: {overallStyle.label}
          </div>
          <div className="text-[12.5px] text-text-2 mt-0.5">
            {data.summary.overall_status === 'green' && 'Tüm kontroller başarılı. Sistemde bilinen anomali yok.'}
            {data.summary.overall_status === 'yellow' && `${data.summary.yellow} kontrolde küçük uyarı var; gözden geçirilebilir.`}
            {data.summary.overall_status === 'red' && `${data.summary.red} kontrolde ciddi sorun tespit edildi; aksiyon önerilir.`}
          </div>
        </div>
      </div>

      {/* Kontrol listesi */}
      <div className="space-y-3">
        {data.checks.map((c) => <CheckCard key={c.key} check={c} />)}
      </div>
    </div>
  );
}

function CheckCard({ check }: { check: DataHealthCheck }) {
  const [open, setOpen] = useState(check.status !== 'green');
  const style = STATUS_STYLE[check.status];
  const Icon = style.icon;
  const expandable = check.samples.length > 0 || check.suggestion !== '—';
  return (
    <div className={`rounded-2xl border ${style.bg} ${style.border} overflow-hidden shadow-sm`}>
      <button
        onClick={() => expandable && setOpen((v) => !v)}
        disabled={!expandable}
        className={`w-full px-5 py-3.5 flex items-center justify-between gap-3 transition ${
          expandable ? 'hover:bg-white/40 cursor-pointer' : 'cursor-default'
        }`}
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <Icon className={`w-5 h-5 flex-shrink-0 ${style.text}`} strokeWidth={2.4} />
          <div className="text-left flex-1 min-w-0">
            <div className="text-[13.5px] font-semibold text-text">{check.label}</div>
            {check.count > 0 && (
              <div className={`text-[11.5px] mt-0.5 ${style.text}`}>
                {check.count} öğe
                {check.total > 0 && check.total !== check.count && (
                  <span className="text-text-3"> / {check.total} toplam</span>
                )}
              </div>
            )}
            {check.count === 0 && (
              <div className="text-[11.5px] text-text-3 mt-0.5">Sorun bulunmadı.</div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider ${style.bg} ${style.text} border ${style.border}`}>
            {style.label}
          </span>
          {expandable && (
            <ChevronRight
              className={`w-4 h-4 transition-transform ${open ? 'rotate-90' : ''} text-text-3`}
              strokeWidth={2.4}
            />
          )}
        </div>
      </button>

      {open && expandable && (
        <div className="px-5 pb-4 bg-white/60 border-t border-border/40">
          {check.samples.length > 0 && (
            <div className="pt-3">
              <div className="text-[10px] uppercase tracking-wider font-bold text-text-3 mb-2">
                Örnekler ({Math.min(check.samples.length, 5)})
              </div>
              <ul className="space-y-1.5">
                {check.samples.map((s, i) => (
                  <li key={`${s.id}-${i}`} className="text-[12.5px] leading-tight">
                    <span className="font-medium text-text">{s.name || `#${s.id}`}</span>
                    <span className="text-text-3"> — {s.detail}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {check.suggestion && check.suggestion !== '—' && (
            <div className="mt-3 text-[11.5px] text-text-2 italic bg-bg-surface2/60 px-3 py-2 rounded-lg border border-border/40">
              💡 {check.suggestion}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
