'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ArrowLeft, Building2, Clock, History, Pencil, Target, User } from 'lucide-react';

import { RestaurantEditModal } from '@/components/restaurant-edit-modal';
import type { PricingHistoryResponse, Restaurant } from '@/lib/api';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(period: string): string {
  const [y, m] = period.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return period;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

const MODEL_COLOR: Record<string, string> = {
  hourly_only: 'bg-blue-50 text-blue-700',
  hourly_plus_package: 'bg-orange-50 text-orange-700',
  threshold_package: 'bg-cream-100 text-yellow-900',
  fixed_monthly: 'bg-green-50 text-green-700',
};

function formatLastChange(iso: string | null | undefined): string | null {
  if (!iso) return null;
  // 'YYYY-MM-DD' veya ISO timestamp olabilir
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return null;
  const [, y, mo, da] = m;
  return `${parseInt(da, 10)} ${TR_MONTHS[parseInt(mo, 10) - 1]} ${y}`;
}

export function RestaurantDetailHeader({
  restaurant,
  period,
  periods,
  modelLabel,
  pricingHistory,
}: {
  restaurant: Restaurant;
  period: string;
  periods: string[];
  modelLabel: string;
  pricingHistory?: PricingHistoryResponse | null;
}) {
  const [editing, setEditing] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);

  const lastChange = pricingHistory?.last_change ?? null;
  const lastChangeLabel = formatLastChange(lastChange?.effective_from ?? null);
  const totalChanges = pricingHistory?.history?.length ?? 0;

  return (
    <>
      {/* ────────── HERO ────────── */}
      <section className="relative z-20 rounded-3xl shadow-lg mb-6">
        <div className="absolute inset-0 overflow-hidden rounded-3xl pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-br from-brand-dark via-brand to-blue-600" />
          <div
            className="absolute inset-0 opacity-30 mix-blend-overlay"
            style={{
              backgroundImage:
                'radial-gradient(circle at 20% 20%, rgba(255,255,255,.4) 0%, transparent 40%), radial-gradient(circle at 80% 70%, rgba(255,200,100,.3) 0%, transparent 50%)',
            }}
          />
          <div
            className="absolute inset-0 opacity-[0.07]"
            style={{
              backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />
        </div>
        <div className="relative px-7 py-7 text-white flex items-start justify-between gap-6 flex-wrap">
          <div className="flex-1 min-w-0">
            <Link
              href="/restoranlar"
              className="text-[11px] font-medium tracking-[0.15em] uppercase text-white/70 mb-2 hover:text-white/90 transition inline-flex items-center gap-1.5"
            >
              <ArrowLeft className="w-3 h-3" strokeWidth={2.4} />
              Restoranlar
            </Link>
            <div className="flex items-center gap-3 flex-wrap mt-1">
              <Building2 className="w-8 h-8 text-white/90" />
              <h1 className="text-4xl font-bold tracking-tight leading-tight">
                {restaurant.brand}
              </h1>
              {restaurant.branch && (
                <span className="text-white/70 font-medium text-2xl">
                  · {restaurant.branch}
                </span>
              )}
              <span
                className={`px-2.5 py-1 rounded-full text-[11.5px] font-semibold ${
                  MODEL_COLOR[restaurant.pricing_model ?? ''] ?? 'bg-white/20 text-white'
                }`}
              >
                {modelLabel}
              </span>
            </div>
            <div className="text-white/75 text-sm font-medium flex items-center gap-3 flex-wrap mt-2">
              {restaurant.contact_name && (
                <span className="inline-flex items-center gap-1">
                  <User className="w-3.5 h-3.5" strokeWidth={2.2} /> {restaurant.contact_name}
                </span>
              )}
              {restaurant.contact_phone && (
                <span className="font-mono text-white/60">{restaurant.contact_phone}</span>
              )}
              {restaurant.target_headcount != null && restaurant.target_headcount > 0 && (
                <span className="inline-flex items-center gap-1">
                  <Target className="w-3.5 h-3.5" strokeWidth={2.2} /> {restaurant.target_headcount} kurye hedef
                </span>
              )}
              {restaurant.vat_rate != null && (
                <span className="text-white/60">· KDV %{restaurant.vat_rate}</span>
              )}
              {lastChangeLabel && (
                <div className="relative">
                  <button
                    onClick={() => setHistoryOpen((v) => !v)}
                    className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-white/15 border border-white/25 text-[11px] font-semibold hover:bg-white/25 transition"
                    title="Tarife değişim geçmişini gör"
                  >
                    <Clock className="w-3 h-3" strokeWidth={2.4} />
                    Tarife güncellendi: {lastChangeLabel}
                    {totalChanges > 1 && (
                      <span className="text-white/65">· {totalChanges} kayıt</span>
                    )}
                  </button>
                  {historyOpen && pricingHistory && (
                    <>
                      <div className="fixed inset-0 z-30" onClick={() => setHistoryOpen(false)} />
                      <PricingHistoryPopover
                        history={pricingHistory.history}
                        onClose={() => setHistoryOpen(false)}
                      />
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Ay seçici + düzenle */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex gap-1 bg-white/15 backdrop-blur-sm border border-white/25 rounded-xl p-1">
              {periods.slice(0, 4).map((p) => (
                <Link
                  key={p}
                  href={`/restoranlar/${restaurant.id}?ay=${p}`}
                  className={`px-2.5 py-1 rounded-lg text-[12.5px] font-semibold transition ${
                    p === period
                      ? 'bg-white text-brand shadow-sm'
                      : 'text-white/80 hover:bg-white/15'
                  }`}
                >
                  {formatPeriod(p)}
                </Link>
              ))}
            </div>
            <button
              onClick={() => setEditing(true)}
              className="px-3.5 py-2 rounded-xl bg-white/15 backdrop-blur-sm border border-white/25 text-white text-sm font-semibold hover:bg-white/25 transition inline-flex items-center gap-1.5"
            >
              <Pencil className="w-3.5 h-3.5" strokeWidth={2.4} />
              <span>Düzenle</span>
            </button>
          </div>
        </div>
      </section>

      {editing && (
        <RestaurantEditModal
          restaurant={restaurant}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  );
}


function PricingHistoryPopover({
  history, onClose,
}: {
  history: PricingHistoryResponse['history'];
  onClose: () => void;
}) {
  return (
    <div className="absolute left-0 mt-1.5 z-40 w-[420px] bg-white text-text rounded-xl shadow-2xl border border-border overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
      <div className="px-4 py-2.5 bg-cream-50/80 border-b border-border flex items-center justify-between">
        <div className="text-[11px] uppercase tracking-wider font-bold text-text-2 inline-flex items-center gap-2">
          <History className="w-3.5 h-3.5" strokeWidth={2.4} />
          Tarife Değişim Geçmişi
        </div>
        <span className="text-[10px] text-text-3">
          {history.length} kayıt
        </span>
      </div>
      {history.length === 0 ? (
        <div className="px-4 py-6 text-center text-text-3 text-[12px] italic">
          Henüz tarife değişikliği kaydedilmemiş.
        </div>
      ) : (
        <ul className="divide-y divide-border max-h-[360px] overflow-y-auto">
          {history.map((h, idx) => (
            <li key={h.id} className="px-4 py-2.5 hover:bg-cream-50/60 transition">
              <div className="flex items-center justify-between mb-1">
                <div className="text-[12px] font-semibold text-text inline-flex items-center gap-1.5">
                  <Clock className="w-3 h-3 text-brand" strokeWidth={2.4} />
                  {formatLastChange(h.effective_from)}
                  {idx === 0 && (
                    <span className="text-[9px] uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 px-1.5 py-0.5 rounded font-bold ml-1">
                      Aktif
                    </span>
                  )}
                </div>
                {h.note && (
                  <span className="text-[10px] text-text-3 italic">{h.note}</span>
                )}
              </div>
              <div className="text-[11px] text-text-2 grid grid-cols-2 gap-x-3 gap-y-0.5 font-mono">
                {h.pricing_model && (
                  <span className="col-span-2 text-text-3 mb-0.5">
                    Model: <span className="text-text font-semibold">{h.pricing_model}</span>
                  </span>
                )}
                {(h.hourly_rate ?? 0) > 0 && (
                  <span>Saatlik: <span className="text-text">{h.hourly_rate} ₺</span></span>
                )}
                {(h.package_rate ?? 0) > 0 && (
                  <span>Paket: <span className="text-text">{h.package_rate} ₺</span></span>
                )}
                {(h.package_threshold ?? 0) > 0 && (
                  <span>Eşik: <span className="text-text">{h.package_threshold} paket</span></span>
                )}
                {(h.package_rate_low ?? 0) > 0 && (
                  <span>Düşük: <span className="text-text">{h.package_rate_low} ₺</span></span>
                )}
                {(h.package_rate_high ?? 0) > 0 && (
                  <span>Yüksek: <span className="text-text">{h.package_rate_high} ₺</span></span>
                )}
                {(h.fixed_monthly_fee ?? 0) > 0 && (
                  <span>Sabit aylık: <span className="text-text">{h.fixed_monthly_fee} ₺</span></span>
                )}
                {(h.vat_rate ?? 0) > 0 && (
                  <span>KDV: <span className="text-text">%{h.vat_rate}</span></span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      <div className="px-4 py-2 bg-bg-surface text-[10px] text-text-3 border-t border-border">
        Hesaplamalar her entry'nin tarihinde geçerli olan tarifeyle yapılır.
      </div>
    </div>
  );
}
