'use client';

import Link from 'next/link';
import clsx from 'clsx';
import type { SidebarCounts } from '@/lib/api';

type NavKey =
  | 'dashboard' | 'personel' | 'puantaj' | 'puantaj-onay' | 'hakedis-onay'
  | 'kesintiler' | 'ekipman' | 'avans' | 'motor' | 'muhasebe-degisim'
  | 'talepler' | 'restoranlar' | 'faturalar' | 'bordro' | 'kar-zarar';

type BadgeKind = 'new' | 'warn' | 'default';

type NavItem = {
  key: NavKey;
  label: string;
  href: string;
  section: string;
  countKey?: keyof SidebarCounts;
  badgeKind?: BadgeKind;
};

const NAV: NavItem[] = [
  { key: 'dashboard', label: 'Genel Bakış', href: '/', section: 'Genel' },
  { key: 'personel', label: 'Personel', href: '/personel', section: 'Operasyon', countKey: 'personel' },
  { key: 'puantaj', label: 'Puantaj', href: '/puantaj', section: 'Operasyon' },
  { key: 'puantaj-onay', label: 'Puantaj Onayları', href: '/puantaj-onaylari', section: 'Operasyon', countKey: 'puantaj_onay', badgeKind: 'warn' },
  { key: 'hakedis-onay', label: 'Hakediş Onayları', href: '/hakedis-onaylari', section: 'Operasyon', countKey: 'hakedis_onay' },
  { key: 'kesintiler', label: 'Kesintiler', href: '/kesintiler', section: 'Operasyon' },
  { key: 'ekipman', label: 'Ekipman & Zimmet', href: '/ekipman-zimmet', section: 'Operasyon' },
  { key: 'talepler', label: 'Talepler (Avans · Motor · Muhasebe)', href: '/talepler', section: 'Operasyon', countKey: 'talepler', badgeKind: 'new' },
  { key: 'restoranlar', label: 'Restoranlar', href: '/restoranlar', section: 'Satış', countKey: 'restoranlar' },
  { key: 'faturalar', label: 'Faturalar', href: '/faturalar', section: 'Finans' },
  { key: 'bordro', label: 'Bordro', href: '/bordro', section: 'Finans' },
  { key: 'kar-zarar', label: 'Kâr-Zarar Raporu', href: '/kar-zarar', section: 'Finans' },
];

export function Sidebar({ active, counts }: { active: NavKey; counts?: SidebarCounts | null }) {
  const sections = ['Genel', 'Operasyon', 'Satış', 'Finans'] as const;

  return (
    <aside className="bg-bg-surface border-r border-border p-5 sticky top-0 h-screen overflow-y-auto flex flex-col">
      {/* Brand */}
      <div className="flex items-center gap-3 px-2 pb-5 border-b border-border mb-4">
        <div className="w-[34px] h-[34px] bg-brand rounded-[9px] flex items-center justify-center text-white font-bold text-base shadow-[0_4px_10px_rgba(15,82,186,0.3)]">
          Ç
        </div>
        <div>
          <div className="font-display font-semibold text-[15px] tracking-tight">
            çat<span className="font-bold">kapında</span>
          </div>
          <div className="text-[11px] text-text-3 mt-0.5 font-medium">Yönetim Paneli</div>
        </div>
      </div>

      {sections.map((sec) => (
        <div key={sec}>
          <div className="px-3 pt-3 pb-1.5 text-[10px] font-bold text-text-3 tracking-[0.1em] uppercase">
            {sec}
          </div>
          {NAV.filter((n) => n.section === sec).map((item) => {
            const value = item.countKey && counts ? counts[item.countKey] : undefined;
            const showBadge = typeof value === 'number' && value > 0;

            return (
              <Link
                key={item.key}
                href={item.href}
                className={clsx(
                  'flex items-center gap-3 px-2.5 py-2 rounded-md text-[13.5px] font-medium transition mb-px',
                  active === item.key
                    ? 'bg-brand text-white shadow-[0_4px_14px_rgba(15,82,186,0.3)]'
                    : 'text-text-2 hover:bg-bg-surface2 hover:text-text'
                )}
              >
                <span>{item.label}</span>
                {showBadge && (
                  <span
                    className={clsx(
                      'ml-auto px-2 py-0.5 rounded-full text-[11px] font-semibold tabular-nums',
                      active === item.key
                        ? 'bg-white/20 text-white'
                        : item.badgeKind === 'new'
                        ? 'bg-brand text-white'
                        : item.badgeKind === 'warn'
                        ? 'bg-yellow-500 text-white'
                        : 'bg-bg-surface2 text-text-3'
                    )}
                  >
                    {value}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      ))}
    </aside>
  );
}
