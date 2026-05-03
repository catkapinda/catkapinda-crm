import { Sidebar } from '@/components/sidebar';
import { listPersonnel, type Personnel } from '@/lib/api';

export const dynamic = 'force-dynamic';

export default async function PersonelPage() {
  let personnel: Personnel[] = [];
  let error: string | null = null;
  try {
    personnel = await listPersonnel('Aktif');
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  const kuryeCount = personnel.filter(p => p.role === 'Kurye').length;
  const yonetimCount = personnel.filter(p => ['Bölge Müdürü', 'Kaptan', 'Restoran Takım Şefi'].includes(p.role ?? '')).length;
  const jokerCount = personnel.filter(p => p.role === 'Joker').length;

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="personel" />
      <main className="p-8 max-w-[1500px]">
        <header className="mb-6">
          <div className="text-[13px] text-text-3 font-medium mb-1.5">
            Operasyon · <span className="text-brand">Personel</span>
          </div>
          <h1 className="font-display text-[30px] font-semibold tracking-tight leading-tight">Personel</h1>
          <div className="text-text-3 text-sm mt-1 font-medium">
            {error ? '⚠ Veriler yüklenemedi' : `${personnel.length} aktif personel · 18 restoranda görev başında`}
          </div>
        </header>

        {/* Hero Strip */}
        <div className="bg-bg-surface border border-border rounded-2xl shadow-md flex overflow-hidden mb-6">
          <HeroCell label="Toplam Aktif" value={personnel.length.toString()} brand meta="canlı veri · Supabase" />
          <HeroCell label="Kurye" value={kuryeCount.toString()} meta="%92 ekibin" />
          <HeroCell label="Yönetim" value={yonetimCount.toString()} meta="BM · Kaptan · Şef" />
          <HeroCell label="Joker" value={jokerCount.toString()} meta="88K ₺ KDV dahil/ay" />
        </div>

        {/* Tabs */}
        <div className="bg-bg-surface border border-border rounded-2xl p-1.5 shadow-sm w-fit mb-4 flex gap-1">
          <button className="px-4 py-2 rounded-lg bg-brand text-white text-sm font-medium shadow-sm">
            Aktif <span className="ml-1.5 bg-white/20 px-2 py-0.5 rounded-full text-[11px]">{personnel.length}</span>
          </button>
          <button className="px-4 py-2 rounded-lg text-text-2 hover:bg-bg-surface2 text-sm font-medium">
            Pasif <span className="ml-1.5 bg-bg-surface2 px-2 py-0.5 rounded-full text-[11px]">11</span>
          </button>
          <button className="px-4 py-2 rounded-lg text-text-2 hover:bg-bg-surface2 text-sm font-medium">
            Kara Liste <span className="ml-1.5 bg-bg-surface2 px-2 py-0.5 rounded-full text-[11px]">3</span>
          </button>
        </div>

        {/* Cards Grid */}
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
            <div className="mt-1 text-xs text-red-600">
              Backend: https://crmcatkapinda-v3-api.onrender.com/api/health/db kontrol edin.
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
            {personnel.map(p => (
              <PersonCard key={p.id} p={p} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function HeroCell({
  label, value, meta, brand,
}: { label: string; value: string; meta?: string; brand?: boolean }) {
  return (
    <div
      className={`flex-1 px-5 py-4 border-r border-border last:border-r-0 ${
        brand ? 'bg-gradient-to-br from-brand-dark to-brand text-white' : ''
      }`}
    >
      <div className={`text-[11px] font-semibold uppercase tracking-wider ${brand ? 'opacity-85' : 'text-text-3'}`}>
        {label}
      </div>
      <div className="font-display text-2xl font-bold tracking-tight mt-1 num">{value}</div>
      {meta && <div className={`text-[11.5px] mt-1 ${brand ? 'opacity-85' : 'text-text-3'}`}>{meta}</div>}
    </div>
  );
}

const AVATAR_GRADIENTS = [
  'from-blue-700 to-blue-500',
  'from-blue-900 to-blue-700',
  'from-yellow-600 to-yellow-400',
  'from-slate-700 to-slate-500',
];

function PersonCard({ p }: { p: Personnel }) {
  const initials = (p.full_name ?? '?').split(' ').filter(Boolean).slice(0, 2).map(w => w[0]?.toUpperCase()).join('');
  const grad = AVATAR_GRADIENTS[(p.id ?? 0) % AVATAR_GRADIENTS.length];
  const role = p.role ?? '?';
  const isKurye = role === 'Kurye';
  const isJoker = role === 'Joker';
  const isBM = role === 'Bölge Müdürü';

  return (
    <div className="bg-bg-surface border border-border rounded-2xl shadow-sm overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer">
      {/* Cover */}
      <div
        className={`h-12 ${
          isKurye ? 'bg-gradient-to-br from-blue-100 to-blue-200'
          : isJoker ? 'bg-gradient-to-br from-yellow-100 to-yellow-200'
          : isBM ? 'bg-gradient-to-br from-slate-800 to-slate-700'
          : 'bg-gradient-to-br from-cream-100 to-cream-200'
        }`}
      >
        {p.status === 'Aktif' && (
          <div className="w-2.5 h-2.5 rounded-full bg-green-500 ring-2 ring-white absolute mt-3 ml-auto mr-3 right-3" />
        )}
      </div>

      {/* Body */}
      <div className="px-4 pt-3 pb-4 relative">
        <div
          className={`absolute -top-7 left-4 w-14 h-14 rounded-full bg-gradient-to-br ${grad} text-white font-bold flex items-center justify-center text-base ring-[3px] ring-white shadow-sm`}
        >
          {initials || '?'}
        </div>
        <div className="pt-9">
          <div className="font-display font-semibold text-[15px] tracking-tight truncate">{p.full_name ?? '—'}</div>
          <div className="flex gap-1.5 items-center mt-1 flex-wrap">
            <span className="font-mono text-[11px] text-text-3 font-medium">{p.person_code ?? '—'}</span>
            <span className="text-text-3 text-xs">·</span>
            <span
              className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                isKurye ? 'bg-brand-soft text-brand'
                : isJoker ? 'bg-cream-100 text-yellow-800'
                : isBM ? 'bg-text text-white'
                : 'bg-cream-100 text-yellow-900'
              }`}
            >
              {role}
            </span>
          </div>
          {p.current_plate && (
            <div className="mt-2 inline-flex font-mono text-[11px] text-text-3 bg-bg-surface2 px-2 py-0.5 rounded">
              {p.current_plate}
            </div>
          )}
          {p.phone && (
            <div className="mt-2 font-mono text-xs text-text-2">{p.phone}</div>
          )}
        </div>
      </div>
    </div>
  );
}
