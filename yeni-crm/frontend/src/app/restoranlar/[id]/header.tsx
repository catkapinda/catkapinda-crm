'use client';

import Link from 'next/link';
import { useState } from 'react';

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
      <header className="flex justify-between items-end gap-5 flex-wrap mb-6">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap mb-1.5">
            <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">
              {restaurant.brand}
            </h1>
            {restaurant.branch && (
              <span className="text-text-3 font-medium text-xl">
                · {restaurant.branch}
              </span>
            )}
            <span
              className={`px-2.5 py-1 rounded-full text-[11.5px] font-semibold ${
                MODEL_COLOR[restaurant.pricing_model ?? ''] ?? 'bg-bg-surface2 text-text-2'
              }`}
            >
              {modelLabel}
            </span>
          </div>
          <div className="text-text-3 text-sm font-medium flex items-center gap-3 flex-wrap">
            {restaurant.contact_name && (
              <span>👤 {restaurant.contact_name}</span>
            )}
            {restaurant.contact_phone && (
              <span className="font-mono">{restaurant.contact_phone}</span>
            )}
            {restaurant.target_headcount != null && restaurant.target_headcount > 0 && (
              <span>🎯 {restaurant.target_headcount} kurye</span>
            )}
            {restaurant.vat_rate != null && (
              <span>· KDV %{restaurant.vat_rate}</span>
            )}
          </div>
        </div>

        {/* Ay seçici + düzenle */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex gap-1 bg-bg-surface border border-border rounded-xl p-1 shadow-sm">
            {periods.slice(0, 4).map((p) => (
              <Link
                key={p}
                href={`/restoranlar/${restaurant.id}?ay=${p}`}
                className={`px-2.5 py-1 rounded-lg text-[12.5px] font-medium transition ${
                  p === period
                    ? 'bg-brand text-white shadow-sm'
                    : 'text-text-2 hover:bg-bg-surface2'
                }`}
              >
                {formatPeriod(p)}
              </Link>
            ))}
          </div>
          <button
            onClick={() => setEditing(true)}
            className="px-3.5 py-2 rounded-xl bg-brand text-white text-sm font-semibold shadow-sm hover:bg-brand-dark transition flex items-center gap-1.5"
          >
            <span>✎</span>
            <span>Düzenle</span>
          </button>
        </div>
      </header>

      {editing && (
        <RestaurantEditModal
          restaurant={restaurant}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  );
}
