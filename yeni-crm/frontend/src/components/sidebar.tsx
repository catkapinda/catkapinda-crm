'use client';

import Link from 'next/link';
import clsx from 'clsx';
import {
  Activity, BadgeCheck, BarChart3, Bike, Box, Building2, Calendar,
  CheckCircle2, ClipboardCheck, Coins, FileSpreadsheet, FileText,
  HeartPulse, Home, LayoutGrid, MinusCircle, RefreshCw, Sparkles, Store,
  TrendingUp, UserCheck, Users, Wallet, ShieldCheck, ShoppingBag,
  type LucideIcon,
} from 'lucide-react';
import type { SidebarCounts } from '@/lib/api';

type NavKey =
  | 'dashboard' | 'personel' | 'puantaj' | 'puantaj-onay' | 'hakedis-onay'
  | 'kesintiler' | 'ekipman' | 'avans' | 'motor' | 'muhasebe-degisim'
  | 'talepler' | 'avans-talepleri' | 'profil-onay' | 'box-geri-alim'
  | 'restoranlar' | 'faturalar' | 'bordro' | 'kar-zarar' | 'restoran-raporlari'
  | 'tahsilatlar' | 'veri-sagligi';

type BadgeKind = 'new' | 'warn' | 'default';

type NavItem = {
  key: NavKey;
  label: string;
  href: string;
  section: SectionName;
  icon: LucideIcon;
  countKey?: keyof SidebarCounts;
  badgeKind?: BadgeKind;
};

type SectionName = 'Genel' | 'Operasyon' | 'Onaylar' | 'Satış' | 'Finans';

const SECTION_ICONS: Record<SectionName, LucideIcon> = {
  Genel: Home,
  Operasyon: Activity,
  Onaylar: ShieldCheck,
  Satış: ShoppingBag,
  Finans: TrendingUp,
};

const NAV: NavItem[] = [
  { key: 'dashboard', label: 'Genel Bakış', href: '/', section: 'Genel', icon: LayoutGrid },
  { key: 'personel', label: 'Personel', href: '/personel', section: 'Operasyon', icon: Users, countKey: 'personel' },
  { key: 'puantaj', label: 'Puantaj', href: '/puantaj', section: 'Operasyon', icon: Calendar },
  { key: 'kesintiler', label: 'Kesintiler', href: '/kesintiler', section: 'Operasyon', icon: MinusCircle },
  { key: 'ekipman', label: 'Ekipman & Zimmet', href: '/ekipman-zimmet', section: 'Operasyon', icon: Bike },
  { key: 'box-geri-alim', label: 'Box Geri Alım', href: '/box-geri-alim', section: 'Operasyon', icon: Box },
  { key: 'avans-talepleri', label: 'Avans Talepleri', href: '/avans-talepleri', section: 'Operasyon', icon: Wallet, countKey: 'avans', badgeKind: 'warn' },
  { key: 'talepler', label: 'Motor ve Muhasebe Değişikliği', href: '/talepler', section: 'Operasyon', icon: RefreshCw, countKey: 'talepler', badgeKind: 'new' },
  // Onaylar
  { key: 'puantaj-onay', label: 'Puantaj Onayları', href: '/puantaj-onaylari', section: 'Onaylar', icon: ClipboardCheck, countKey: 'puantaj_onay', badgeKind: 'warn' },
  { key: 'hakedis-onay', label: 'Hakediş Onayları', href: '/hakedis-onaylari', section: 'Onaylar', icon: BadgeCheck, countKey: 'hakedis_onay' },
  { key: 'profil-onay', label: 'Profil Onayları', href: '/profil-onaylari', section: 'Onaylar', icon: UserCheck, countKey: 'profil_onay', badgeKind: 'warn' },
  { key: 'restoranlar', label: 'Restoranlar', href: '/restoranlar', section: 'Satış', icon: Store, countKey: 'restoranlar' },
  { key: 'restoran-raporlari', label: 'Restoran Raporları', href: '/raporlar', section: 'Satış', icon: BarChart3 },
  { key: 'faturalar', label: 'Faturalar', href: '/faturalar', section: 'Finans', icon: FileText },
  { key: 'tahsilatlar', label: 'Tahsilatlar', href: '/tahsilatlar', section: 'Finans', icon: Coins },
  { key: 'bordro', label: 'Bordro', href: '/bordro', section: 'Finans', icon: FileSpreadsheet },
  { key: 'kar-zarar', label: 'Kâr-Zarar Raporu', href: '/kar-zarar', section: 'Finans', icon: TrendingUp },
  { key: 'veri-sagligi', label: 'Veri Sağlığı', href: '/veri-sagligi', section: 'Finans', icon: HeartPulse },
];

const SECTIONS: SectionName[] = ['Genel', 'Operasyon', 'Onaylar', 'Satış', 'Finans'];

export function Sidebar({ active, counts }: { active: NavKey; counts?: SidebarCounts | null }) {
  return (
    <aside
      className={clsx(
        'relative bg-gradient-to-b from-bg-surface via-bg-surface to-blue-50/40',
        'border-r border-border/80',
        'p-4 sticky top-0 h-screen overflow-y-auto flex flex-col',
        'animate-sidebar-in',
      )}
    >
      {/* Decorative orbs */}
      <div className="pointer-events-none absolute -top-16 -left-16 w-44 h-44 rounded-full bg-blue-300/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-20 -right-12 w-40 h-40 rounded-full bg-cyan-300/15 blur-3xl" />

      {/* Brand */}
      <div className="relative flex items-center gap-3 px-1.5 pb-4 mb-3 border-b border-border/70">
        <div className="relative group">
          {/* Glow halo */}
          <div className="absolute inset-0 rounded-[12px] bg-brand/30 blur-xl scale-110 opacity-60 group-hover:opacity-90 transition-opacity" />
          <div
            className={clsx(
              'relative w-[38px] h-[38px] rounded-[12px]',
              'bg-gradient-to-br from-blue-500 via-blue-600 to-blue-800',
              'flex items-center justify-center',
              'text-white font-bold text-[17px] font-display',
              'shadow-[0_6px_18px_rgba(15,82,186,0.45)]',
              'ring-1 ring-white/40',
              'transition-transform group-hover:scale-105',
            )}
          >
            Ç
          </div>
        </div>
        <div className="min-w-0">
          <div className="font-display font-semibold text-[15.5px] tracking-tight leading-tight">
            çat<span className="font-bold text-brand">kapında</span>
          </div>
          <div className="text-[10.5px] text-text-3 mt-0.5 font-medium tracking-wide uppercase">
            Yönetim Paneli
          </div>
        </div>
      </div>

      {/* Sections */}
      <nav className="relative flex-1 space-y-2">
        {SECTIONS.map((sec) => {
          const SecIcon = SECTION_ICONS[sec];
          const items = NAV.filter((n) => n.section === sec);
          if (items.length === 0) return null;

          // Section'daki toplam bekleyen iş — başlığa rozet için
          const sectionPending = items.reduce((sum, it) => {
            if (it.badgeKind === 'warn' && it.countKey && counts) {
              const v = counts[it.countKey];
              if (typeof v === 'number') return sum + v;
            }
            return sum;
          }, 0);

          return (
            <div key={sec}>
              {/* Section header */}
              <div className="flex items-center gap-1.5 px-2 pt-2 pb-1">
                <SecIcon className="w-3 h-3 text-text-3/70" strokeWidth={2.4} />
                <span className="text-[10px] font-bold text-text-3/80 tracking-[0.12em] uppercase">
                  {sec}
                </span>
                {sec === 'Onaylar' && sectionPending > 0 && (
                  <span className="ml-auto inline-flex items-center justify-center min-w-[18px] h-[18px] px-1.5 rounded-full bg-amber-500/90 text-white text-[10px] font-bold shadow-sm animate-pulse-soft">
                    {sectionPending}
                  </span>
                )}
              </div>

              {/* Section items */}
              <div className="space-y-px">
                {items.map((item) => {
                  const value = item.countKey && counts ? counts[item.countKey] : undefined;
                  const showBadge = typeof value === 'number' && value > 0;
                  const isActive = active === item.key;
                  const Icon = item.icon;

                  return (
                    <Link
                      key={item.key}
                      href={item.href}
                      className={clsx(
                        'group relative flex items-center gap-2.5 pl-3 pr-2.5 py-2 rounded-xl',
                        'text-[13px] font-medium',
                        'transition-all duration-200 ease-out',
                        isActive
                          ? [
                              'bg-gradient-to-r from-blue-600 to-blue-500',
                              'text-white',
                              'shadow-[0_6px_18px_rgba(15,82,186,0.35)]',
                            ].join(' ')
                          : [
                              'text-text-2',
                              'hover:bg-blue-50/80 hover:text-blue-900',
                              'hover:translate-x-0.5',
                              'hover:shadow-sm',
                            ].join(' '),
                      )}
                    >
                      {/* Sol gradient bar — sadece active */}
                      {isActive && (
                        <span className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-[3px] w-[3px] h-[60%] rounded-full bg-gradient-to-b from-cyan-300 to-blue-400 shadow-[0_0_8px_rgba(56,189,248,0.7)]" />
                      )}

                      <Icon
                        className={clsx(
                          'flex-shrink-0 transition-transform',
                          isActive
                            ? 'w-[15px] h-[15px] text-white'
                            : 'w-[15px] h-[15px] text-text-3 group-hover:text-blue-600 group-hover:scale-110',
                        )}
                        strokeWidth={2.2}
                      />
                      <span className="truncate flex-1">{item.label}</span>

                      {showBadge && (
                        <span
                          className={clsx(
                            'inline-flex items-center justify-center min-w-[20px] h-[18px] px-1.5 rounded-full',
                            'text-[10.5px] font-bold tabular-nums tracking-tight',
                            isActive
                              ? 'bg-white/25 text-white ring-1 ring-white/30'
                              : item.badgeKind === 'new'
                              ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-sm'
                              : item.badgeKind === 'warn'
                              ? 'bg-gradient-to-r from-amber-400 to-amber-500 text-white shadow-sm animate-pulse-soft'
                              : 'bg-bg-surface2 text-text-3 ring-1 ring-border',
                          )}
                        >
                          {value}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>

      {/* Footer — versiyon damgası */}
      <div className="relative pt-3 mt-2 border-t border-border/60 px-2">
        <div className="flex items-center gap-1.5 text-[10px] text-text-3/70">
          <Sparkles className="w-3 h-3 text-blue-500/60" strokeWidth={2.4} />
          <span className="font-semibold tracking-wide">v3 · Premium</span>
          <span className="ml-auto font-mono">staging</span>
        </div>
      </div>
    </aside>
  );
}
