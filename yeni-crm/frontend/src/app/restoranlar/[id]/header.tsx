'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ArrowLeft, Building2, Pencil, Target, User } from 'lucide-react';

import { RestaurantEditModal } from '@/components/restaurant-edit-modal';
import type { Restaurant } from '@/lib/api';

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

export function RestaurantDetailHeader({
  restaurant,
  period,
  periods,
  modelLabel,
}: {
  restaurant: Restaurant;
  period: string;
  periods: string[];
  modelLabel: string;
}) {
  const [editing, setEditing] = useState(false);

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
