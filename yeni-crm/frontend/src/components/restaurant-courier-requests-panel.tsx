'use client';

/**
 * Restoran detayında "Kurye Talepleri" şeffaflık paneli.
 *
 * - Ek kurye / azaltma taleplerini listeler
 * - Yeni Talep modal: tarih + tip + sayı + gerekçe
 * - Her satırda "Karşılandı" işaretle (fulfilled_at otomatik bugün) veya
 *   "İptal" / "Sil" aksiyonları
 * - Üst KPI: Bekleyen ek / Bekleyen azaltma / Bu ay karşılanan
 */
import { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle, CheckCircle2, Clock, Loader2, MinusCircle,
  Plus, PlusCircle, Sparkles, Trash2, X,
} from 'lucide-react';

import {
  createRestaurantCourierRequest,
  deleteRestaurantCourierRequest,
  listRestaurantCourierRequests,
  updateRestaurantCourierRequest,
  type RestaurantCourierRequest,
  type RestaurantRestaurantCourierRequestListResponse,
} from '@/lib/api';

function todayIso(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const [y, m, dd] = iso.split('-').map((s) => parseInt(s, 10));
  if (!y || !m || !dd) return iso;
  return `${dd.toString().padStart(2, '0')}.${m.toString().padStart(2, '0')}.${y}`;
}

const TYPE_META: Record<
  'add' | 'remove',
  { label: string; color: string; ring: string; icon: typeof PlusCircle }
> = {
  add: {
    label: 'Ek kurye',
    color: 'text-emerald-700',
    ring: 'bg-emerald-50 ring-emerald-200',
    icon: PlusCircle,
  },
  remove: {
    label: 'Azaltma',
    color: 'text-rose-700',
    ring: 'bg-rose-50 ring-rose-200',
    icon: MinusCircle,
  },
};

export function RestaurantCourierRequestsPanel({
  restaurantId,
}: {
  restaurantId: number;
}) {
  const [data, setData] = useState<RestaurantCourierRequestListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [showAll, setShowAll] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const res = await listRestaurantCourierRequests(restaurantId);
      setData(res);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Talepler alınamadı');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [restaurantId]);

  const summary = data?.summary;
  const items = data?.items ?? [];
  const openItems = items.filter((i) => i.status === 'open');
  const fulfilledItems = items.filter((i) => i.status === 'fulfilled');
  const visibleHistory = showAll ? items : items.slice(0, 6);

  async function markFulfilled(id: number) {
    try {
      await updateRestaurantCourierRequest(restaurantId, id, {
        status: 'fulfilled',
        fulfilled_at: todayIso(),
      });
      await refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Güncellenemedi');
    }
  }

  async function cancel(id: number) {
    if (!confirm('Bu talebi iptal etmek istediğinden emin misin?')) return;
    try {
      await updateRestaurantCourierRequest(restaurantId, id, { status: 'cancelled' });
      await refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Güncellenemedi');
    }
  }

  async function remove(id: number) {
    if (!confirm('Talep kalıcı olarak silinsin mi?')) return;
    try {
      await deleteRestaurantCourierRequest(restaurantId, id);
      await refresh();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Silinemedi');
    }
  }

  return (
    <section className="bg-white border border-border rounded-2xl shadow-sm mb-6 overflow-hidden">
      {/* Header — premium gradient bar */}
      <div className="relative px-5 py-3.5 bg-gradient-to-r from-brand-dark via-brand to-blue-600 overflow-hidden">
        <div
          className="absolute inset-0 opacity-30 pointer-events-none"
          style={{
            backgroundImage:
              'radial-gradient(circle at 30% 30%, rgba(255,255,255,.3) 0%, transparent 50%), radial-gradient(circle at 80% 70%, rgba(255,200,100,.25) 0%, transparent 60%)',
          }}
        />
        <div className="relative flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2.5 text-white">
            <div className="w-9 h-9 rounded-xl bg-white/15 ring-1 ring-white/25 flex items-center justify-center">
              <Sparkles className="w-4 h-4" strokeWidth={2.2} />
            </div>
            <div>
              <div className="text-[10.5px] uppercase tracking-[0.18em] text-white/65 font-bold">
                Operasyonel Talep
              </div>
              <h3 className="font-display text-[17px] font-bold tracking-tight">
                Kurye Talepleri
              </h3>
            </div>
          </div>
          <button
            onClick={() => setShowNew(true)}
            className="px-3.5 py-2 rounded-xl bg-white text-brand-dark text-[12.5px] font-bold shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all inline-flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" strokeWidth={2.6} />
            Yeni Talep
          </button>
        </div>
      </div>

      {/* Summary KPI strip */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-border">
          <SummaryStat
            label="Bekleyen ek kurye"
            value={summary.open_add_count}
            icon={PlusCircle}
            accent="emerald"
          />
          <SummaryStat
            label="Bekleyen azaltma"
            value={summary.open_remove_count}
            icon={MinusCircle}
            accent="rose"
          />
          <SummaryStat
            label="Karşılanmış"
            value={summary.fulfilled_count}
            icon={CheckCircle2}
            accent="sky"
          />
          <SummaryStat
            label="Son bekleyen tarih"
            value={formatDate(summary.latest_open)}
            icon={Clock}
            accent="amber"
            text
          />
        </div>
      )}

      {/* Body */}
      <div className="p-5">
        {loading ? (
          <div className="flex items-center gap-2 text-text-3 text-[13px]">
            <Loader2 className="w-4 h-4 animate-spin" /> Yükleniyor…
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-[12.5px] flex items-start gap-2">
            <AlertCircle className="w-4 h-4 mt-0.5" />
            <span>{error}</span>
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-bg-surface2 flex items-center justify-center text-text-3">
              <Sparkles className="w-6 h-6" strokeWidth={1.6} />
            </div>
            <div className="font-display font-bold text-text mb-1">
              Henüz talep yok
            </div>
            <div className="text-text-3 text-[13px]">
              Ek kurye veya azaltma için "Yeni Talep" oluştur.
            </div>
          </div>
        ) : (
          <>
            {/* Açık talepler — kart şeklinde */}
            {openItems.length > 0 && (
              <div className="mb-5">
                <div className="text-[10.5px] font-bold uppercase tracking-[0.18em] text-text-3 mb-2 flex items-center gap-2">
                  <Clock className="w-3 h-3" strokeWidth={2.4} />
                  Bekleyen ({openItems.length})
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {openItems.map((req) => (
                    <OpenRequestCard
                      key={req.id}
                      req={req}
                      onMarkFulfilled={() => markFulfilled(req.id)}
                      onCancel={() => cancel(req.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Geçmiş — tablo */}
            {(fulfilledItems.length > 0 || openItems.length === 0) && (
              <div>
                <div className="text-[10.5px] font-bold uppercase tracking-[0.18em] text-text-3 mb-2">
                  Geçmiş ({items.length})
                </div>
                <div className="rounded-xl border border-border overflow-hidden">
                  <table className="w-full text-[13px]">
                    <thead className="bg-bg-surface2/60 text-text-3 text-[11px] uppercase tracking-wider">
                      <tr>
                        <th className="text-left px-3 py-2 font-bold">Tip</th>
                        <th className="text-left px-3 py-2 font-bold">Talep tarihi</th>
                        <th className="text-right px-3 py-2 font-bold">Kurye</th>
                        <th className="text-left px-3 py-2 font-bold">Durum</th>
                        <th className="text-left px-3 py-2 font-bold">Karşılanma</th>
                        <th className="text-left px-3 py-2 font-bold">Gerekçe</th>
                        <th className="text-right px-3 py-2 font-bold w-12"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleHistory.map((req) => (
                        <HistoryRow
                          key={req.id}
                          req={req}
                          onDelete={() => remove(req.id)}
                          onMarkFulfilled={() => markFulfilled(req.id)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
                {items.length > 6 && (
                  <button
                    onClick={() => setShowAll((v) => !v)}
                    className="mt-2 text-[12px] text-brand hover:text-brand-dark font-semibold transition"
                  >
                    {showAll ? '↑ Daha azını göster' : `↓ Tümünü göster (${items.length})`}
                  </button>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Yeni Talep modal */}
      {showNew && (
        <NewRequestModal
          restaurantId={restaurantId}
          onClose={() => setShowNew(false)}
          onCreated={async () => {
            setShowNew(false);
            await refresh();
          }}
        />
      )}
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────

function SummaryStat({
  label, value, icon: Icon, accent, text,
}: {
  label: string;
  value: number | string;
  icon: typeof Clock;
  accent: 'emerald' | 'rose' | 'sky' | 'amber';
  text?: boolean;
}) {
  const iconBg: Record<string, string> = {
    emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    rose: 'bg-rose-50 text-rose-700 ring-rose-200',
    sky: 'bg-sky-50 text-sky-700 ring-sky-200',
    amber: 'bg-amber-50 text-amber-700 ring-amber-200',
  };
  return (
    <div className="bg-white px-4 py-3 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-xl flex items-center justify-center ring-1 ${iconBg[accent]}`}>
        <Icon className="w-4 h-4" strokeWidth={2.2} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-text-3">
          {label}
        </div>
        <div className={`font-display ${text ? 'text-[14px]' : 'text-[20px]'} font-bold tracking-tight tabular-nums leading-tight truncate`}>
          {value}
        </div>
      </div>
    </div>
  );
}

function OpenRequestCard({
  req, onMarkFulfilled, onCancel,
}: {
  req: RestaurantCourierRequest;
  onMarkFulfilled: () => void;
  onCancel: () => void;
}) {
  const meta = TYPE_META[req.change_type];
  const Icon = meta.icon;
  return (
    <div className={`relative rounded-xl ring-1 ${meta.ring} p-3 hover:shadow-md transition-all`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${meta.color}`} strokeWidth={2.4} />
          <span className={`font-bold text-[13px] ${meta.color}`}>
            {meta.label} · {req.count} kurye
          </span>
        </div>
        <div className="text-[10.5px] text-text-3 font-mono">
          {formatDate(req.request_date)}
        </div>
      </div>
      {req.note && (
        <div className="text-[12px] text-text-2 leading-relaxed mb-3 italic">
          "{req.note}"
        </div>
      )}
      <div className="flex items-center gap-2">
        <button
          onClick={onMarkFulfilled}
          className="flex-1 px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11.5px] font-bold transition inline-flex items-center justify-center gap-1"
        >
          <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={2.4} />
          Karşılandı
        </button>
        <button
          onClick={onCancel}
          className="px-2.5 py-1.5 rounded-lg bg-bg-surface2 hover:bg-rose-50 text-text-2 hover:text-rose-700 text-[11.5px] font-semibold transition inline-flex items-center gap-1"
        >
          <X className="w-3.5 h-3.5" strokeWidth={2.4} />
          İptal
        </button>
      </div>
    </div>
  );
}

function HistoryRow({
  req, onDelete, onMarkFulfilled,
}: {
  req: RestaurantCourierRequest;
  onDelete: () => void;
  onMarkFulfilled: () => void;
}) {
  const meta = TYPE_META[req.change_type];
  const Icon = meta.icon;
  const statusMeta = {
    open: { label: 'Bekliyor', class: 'bg-amber-50 text-amber-800 ring-amber-200' },
    fulfilled: { label: 'Karşılandı', class: 'bg-emerald-50 text-emerald-800 ring-emerald-200' },
    cancelled: { label: 'İptal', class: 'bg-bg-surface2 text-text-3 ring-border' },
  }[req.status];

  return (
    <tr className="border-t border-border hover:bg-bg-surface2/40 transition">
      <td className="px-3 py-2">
        <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold ${meta.ring} ${meta.color}`}>
          <Icon className="w-3 h-3" strokeWidth={2.4} />
          {meta.label}
        </div>
      </td>
      <td className="px-3 py-2 text-text-2 tabular-nums">
        {formatDate(req.request_date)}
      </td>
      <td className="px-3 py-2 text-right tabular-nums font-semibold text-text">
        {req.count}
      </td>
      <td className="px-3 py-2">
        <span className={`inline-block px-1.5 py-0.5 rounded-md text-[10.5px] font-bold ring-1 ${statusMeta.class}`}>
          {statusMeta.label}
        </span>
      </td>
      <td className="px-3 py-2 text-text-2 tabular-nums text-[12px]">
        {formatDate(req.fulfilled_at)}
      </td>
      <td className="px-3 py-2 text-text-3 text-[11.5px] truncate max-w-[200px]" title={req.note ?? ''}>
        {req.note ?? '—'}
      </td>
      <td className="px-3 py-2 text-right">
        <div className="inline-flex items-center gap-0.5">
          {req.status === 'open' && (
            <button
              onClick={onMarkFulfilled}
              className="p-1 rounded hover:bg-emerald-50 text-emerald-700 transition"
              title="Karşılandı işaretle"
            >
              <CheckCircle2 className="w-3.5 h-3.5" strokeWidth={2.4} />
            </button>
          )}
          <button
            onClick={onDelete}
            className="p-1 rounded hover:bg-rose-50 text-text-3 hover:text-rose-700 transition"
            title="Sil"
          >
            <Trash2 className="w-3.5 h-3.5" strokeWidth={2.4} />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ─────────────────────────────────────────────────────────────────
// Yeni Talep modal
// ─────────────────────────────────────────────────────────────────

function NewRequestModal({
  restaurantId, onClose, onCreated,
}: {
  restaurantId: number;
  onClose: () => void;
  onCreated: () => void | Promise<void>;
}) {
  const [date, setDate] = useState<string>(todayIso());
  const [changeType, setChangeType] = useState<'add' | 'remove'>('add');
  const [count, setCount] = useState<number>(1);
  const [note, setNote] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!date) {
      setError('Tarih gerekli.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createRestaurantCourierRequest(restaurantId, {
        request_date: date,
        change_type: changeType,
        count,
        note: note.trim() || null,
      });
      await onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Talep oluşturulamadı');
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden animate-rise"
      >
        <div className="px-5 py-3 bg-gradient-to-r from-brand-dark to-brand flex items-center justify-between text-white">
          <div className="font-display font-bold tracking-tight">Yeni Kurye Talebi</div>
          <button type="button" onClick={onClose} className="p-1 rounded hover:bg-white/15 transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Tip seçimi */}
          <div>
            <label className="block text-[10.5px] font-bold uppercase tracking-[0.18em] text-text-3 mb-1.5">
              Talep tipi
            </label>
            <div className="grid grid-cols-2 gap-2">
              <TypeOption
                active={changeType === 'add'}
                onClick={() => setChangeType('add')}
                icon={PlusCircle}
                label="Ek kurye"
                color="emerald"
              />
              <TypeOption
                active={changeType === 'remove'}
                onClick={() => setChangeType('remove')}
                icon={MinusCircle}
                label="Azaltma"
                color="rose"
              />
            </div>
          </div>

          {/* Tarih + sayı */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[10.5px] font-bold uppercase tracking-[0.18em] text-text-3 mb-1.5">
                Talep tarihi
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg border border-border text-[13px] focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
              />
            </div>
            <div>
              <label className="block text-[10.5px] font-bold uppercase tracking-[0.18em] text-text-3 mb-1.5">
                Kurye sayısı
              </label>
              <input
                type="number"
                min={1}
                max={50}
                value={count}
                onChange={(e) => setCount(Math.max(1, parseInt(e.target.value, 10) || 1))}
                required
                className="w-full px-3 py-2 rounded-lg border border-border text-[13px] tabular-nums focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
              />
            </div>
          </div>

          {/* Not */}
          <div>
            <label className="block text-[10.5px] font-bold uppercase tracking-[0.18em] text-text-3 mb-1.5">
              Gerekçe / Not (opsiyonel)
            </label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="Örn: Hafta sonu yoğunluğu için 2 kurye desteği"
              className="w-full px-3 py-2 rounded-lg border border-border text-[13px] resize-none focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition"
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-2.5 text-red-700 text-[12.5px] flex items-start gap-2">
              <AlertCircle className="w-4 h-4 mt-0.5" /> <span>{error}</span>
            </div>
          )}
        </div>

        <div className="px-5 py-3 bg-bg-surface2/40 border-t border-border flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg text-text-2 text-[12.5px] font-semibold hover:bg-bg-surface transition"
            disabled={submitting}
          >
            Vazgeç
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-1.5 rounded-lg bg-gradient-to-r from-brand-dark to-brand text-white text-[12.5px] font-bold shadow-md hover:shadow-lg transition inline-flex items-center gap-1.5 disabled:opacity-60"
          >
            {submitting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" strokeWidth={2.6} />}
            Talep Oluştur
          </button>
        </div>
      </form>

      <style jsx>{`
        :global(.animate-fade-in) { animation: fade-in 0.18s ease-out both; }
        :global(.animate-rise)    { animation: rise 0.32s cubic-bezier(0.22,1,0.36,1) both; }
        @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
        @keyframes rise    { from { opacity: 0; transform: translateY(14px) scale(0.985); } to { opacity: 1; transform: translateY(0) scale(1); } }
      `}</style>
    </div>
  );
}

function TypeOption({
  active, onClick, icon: Icon, label, color,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof PlusCircle;
  label: string;
  color: 'emerald' | 'rose';
}) {
  const activeMap: Record<string, string> = {
    emerald: 'border-emerald-500 bg-emerald-50 text-emerald-800 ring-2 ring-emerald-500/30',
    rose: 'border-rose-500 bg-rose-50 text-rose-800 ring-2 ring-rose-500/30',
  };
  return (
    <button
      type="button"
      onClick={onClick}
      className={`px-3 py-2.5 rounded-xl border-2 transition flex items-center justify-center gap-2 text-[13px] font-bold ${
        active
          ? activeMap[color]
          : 'border-border text-text-2 hover:border-text-3 bg-bg-surface'
      }`}
    >
      <Icon className="w-4 h-4" strokeWidth={2.4} />
      {label}
    </button>
  );
}
