'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowDownRight, ArrowUpRight, BadgeCheck, ChevronRight,
  Clock, FileText, LogOut, Receipt, Sparkles, TrendingUp,
  User, Wallet, Zap,
} from 'lucide-react';

import { getMyInfo, type CourierMe } from '@/lib/courier-api';

// Backend bordro şemaları arasında uyumluluk:
type RawBordro = {
  total_brut?: number;
  total_deductions?: number;
  total_net?: number;
  toplam_brut?: number;
  kesinti_total?: number;
  sabit_total?: number;
  tevkifat?: number;
  net?: number;
};

type CourierSummary = {
  period: string;
  bordro: RawBordro | null;
  request_stats?: {
    pending_count?: number;
    approved_count?: number;
    rejected_count?: number;
  };
};

function normalizeBordro(b: RawBordro | null | undefined) {
  if (!b) return { total_brut: 0, total_deductions: 0, total_net: 0 };
  const total_brut = b.total_brut ?? b.toplam_brut ?? 0;
  const total_deductions =
    b.total_deductions ??
    ((b.kesinti_total ?? 0) + (b.sabit_total ?? 0) + (b.tevkifat ?? 0));
  const total_net = b.total_net ?? b.net ?? 0;
  return {
    total_brut: Number(total_brut) || 0,
    total_deductions: Number(total_deductions) || 0,
    total_net: Number(total_net) || 0,
  };
}

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string) {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function tr(value: number, digits = 2) {
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function getInitials(name?: string | null) {
  if (!name) return '?';
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('');
}

export default function CourierDashboard() {
  const router = useRouter();
  const [data, setData] = useState<CourierSummary | null>(null);
  const [me, setMe] = useState<CourierMe | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [period, setPeriod] = useState<string>('');
  // Saat-bağımlı selamlama: SSR'da sabit varsayılanla başla, client mount'ta
  // gerçek saate göre güncelle. Aksi halde server saati ↔ client saati farkı
  // hydration mismatch'ine (React #418) yol açıyor.
  const [greeting, setGreeting] = useState('Merhaba');

  useEffect(() => {
    const h = new Date().getHours();
    if (h < 6) setGreeting('İyi geceler');
    else if (h < 12) setGreeting('Günaydın');
    else if (h < 18) setGreeting('Tünaydın');
    else setGreeting('İyi akşamlar');
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('courier_token');
      if (!token) {
        router.push('/kurye');
        return;
      }

      try {
        // Önce mevcut periyodu seç (current month)
        const now = new Date();
        const cur = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        setPeriod(cur);

        const [summaryRes, meData] = await Promise.all([
          fetch(`/api/courier/my-summary?period=${cur}`, {
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          }),
          getMyInfo().catch(() => null),
        ]);

        if (!summaryRes.ok) {
          if (summaryRes.status === 401) {
            localStorage.removeItem('courier_token');
            router.push('/kurye');
            return;
          }
          throw new Error('Veriler yüklenemedi');
        }

        setData(await summaryRes.json());
        setMe(meData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Sunucu hatası');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [router]);

  const handleLogout = async () => {
    const token = localStorage.getItem('courier_token');
    if (token) {
      try {
        await fetch('/api/courier/logout', {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        });
      } catch { /* ignore */ }
    }
    localStorage.removeItem('courier_token');
    router.push('/kurye');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center px-6">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-4">
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 animate-pulse" />
            <div className="absolute inset-2 rounded-xl bg-white flex items-center justify-center overflow-hidden">
              <img
                src="/catkapinda-logo.png?v=3"
                alt=""
                className="w-9 h-9 object-contain"
                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
              />
              <span className="absolute font-display font-bold text-2xl text-blue-600">
                Ç
              </span>
            </div>
          </div>
          <p className="text-slate-600 text-sm font-medium animate-pulse">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center px-6">
        <div className="bg-white border border-red-200 rounded-2xl p-6 max-w-sm shadow-xl">
          <div className="w-12 h-12 rounded-xl bg-red-100 text-red-600 flex items-center justify-center mb-3">
            <Receipt className="w-6 h-6" />
          </div>
          <h2 className="font-bold text-slate-900 mb-2">Veri yüklenemedi</h2>
          <p className="text-sm text-slate-600 mb-4">{error || 'Sunucudan cevap alınamadı'}</p>
          <button
            onClick={() => window.location.reload()}
            className="w-full px-4 py-2.5 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  const bordro = normalizeBordro(data.bordro);
  const stats = data.request_stats ?? {};
  const initials = getInitials(me?.full_name);
  const firstName = me?.full_name?.split(' ')[0] ?? 'Kurye';

  // Bordro durumu: hiç veri yoksa "henüz puantaj yok" göster
  const hasPayrollData = bordro.total_brut > 0 || bordro.total_net > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 pb-24">
      {/* HERO HEADER */}
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-600 via-blue-700 to-blue-900 text-white animate-hero-in">
        {/* Decorative orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-20 -right-20 w-64 h-64 rounded-full bg-cyan-400/20 blur-3xl" />
          <div className="absolute -bottom-20 -left-20 w-72 h-72 rounded-full bg-blue-300/20 blur-3xl" />
        </div>
        {/* Dot pattern */}
        <div
          className="absolute inset-0 opacity-[0.06] pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
            backgroundSize: '20px 20px',
          }}
        />

        <div className="relative px-5 pt-8 pb-32 max-w-2xl mx-auto">
          <div className="flex items-center justify-between mb-7">
            <div className="flex items-center gap-2.5">
              <div className="relative w-9 h-9 rounded-xl bg-white/15 backdrop-blur-md border border-white/20 flex items-center justify-center overflow-hidden">
                <img
                  src="/catkapinda-logo.png?v=3"
                  alt=""
                  className="absolute inset-1 w-7 h-7 object-contain"
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                />
                <span className="font-display font-bold text-base text-white">Ç</span>
              </div>
              <div>
                <div className="font-bold text-sm tracking-tight">Çat Kapında</div>
                <div className="text-[10px] uppercase tracking-widest text-blue-100/60 font-semibold">
                  Kurye Portalı
                </div>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-md border border-white/15 flex items-center justify-center hover:bg-white/20 transition active:scale-95"
              aria-label="Çıkış yap"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-4 mb-3">
            <div className="relative flex-shrink-0">
              <div className="w-16 h-16 rounded-2xl bg-white/15 backdrop-blur-md border-2 border-white/30 shadow-xl flex items-center justify-center overflow-hidden">
                {me?.profile_photo_data ? (
                  <img src={me.profile_photo_data} alt={me.full_name} className="w-full h-full object-cover" />
                ) : (
                  <span className="font-display font-bold text-xl">{initials}</span>
                )}
              </div>
              <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-400 border-2 border-blue-700 flex items-center justify-center">
                <BadgeCheck className="w-3 h-3 text-white" strokeWidth={3} />
              </div>
            </div>
            <div className="min-w-0">
              <p className="text-blue-100/80 text-xs font-medium tracking-wide">
                {greeting},
              </p>
              <h1 className="font-display text-2xl font-bold tracking-tight truncate">
                {firstName}
              </h1>
              <p className="text-blue-100/70 text-xs font-mono mt-0.5">
                {me?.person_code ?? '...'} · {me?.role ?? '...'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* MAIN BORDRO CARD — overlap on hero */}
      <div className="relative max-w-2xl mx-auto px-5 -mt-24 animate-card-in">
        <div className="bg-white rounded-3xl shadow-2xl overflow-hidden ring-1 ring-slate-200/50">
          {/* Top: net amount */}
          <div className="p-6 bg-gradient-to-br from-emerald-50 via-white to-emerald-50/50">
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                  Net Hakediş
                </p>
                <p className="text-xs text-slate-500 mt-0.5">{formatPeriod(period)}</p>
              </div>
              <div className="w-9 h-9 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center">
                <Wallet className="w-4 h-4" strokeWidth={2.4} />
              </div>
            </div>
            <div className="font-display text-4xl font-bold text-slate-900 tabular-nums">
              {tr(bordro.total_net)}
              <span className="text-xl text-slate-400 font-medium ml-1">₺</span>
            </div>
            {!hasPayrollData && (
              <p className="text-xs text-slate-500 mt-2 inline-flex items-center gap-1.5 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200">
                <Sparkles className="w-3 h-3" /> Bu ay henüz puantaj yok
              </p>
            )}
          </div>

          {/* Bottom: brüt + kesinti */}
          <div className="grid grid-cols-2 divide-x divide-slate-100 border-t border-slate-100">
            <div className="p-4">
              <div className="flex items-center gap-1.5 mb-1">
                <ArrowUpRight className="w-3 h-3 text-emerald-600" />
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Brüt</p>
              </div>
              <p className="font-mono font-bold text-slate-900 text-lg tabular-nums">
                {tr(bordro.total_brut)} <span className="text-xs text-slate-400">₺</span>
              </p>
            </div>
            <div className="p-4">
              <div className="flex items-center gap-1.5 mb-1">
                <ArrowDownRight className="w-3 h-3 text-rose-600" />
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Kesinti</p>
              </div>
              <p className="font-mono font-bold text-rose-600 text-lg tabular-nums">
                −{tr(bordro.total_deductions)} <span className="text-xs text-rose-400">₺</span>
              </p>
            </div>
          </div>
        </div>

        {/* Quick action grid */}
        <div className="grid grid-cols-2 gap-3 mt-4 animate-stagger-in">
          <ActionTile
            href="/kurye/bordro"
            label="Bordrolarım"
            sublabel="Geçmiş aylar"
            icon={<Receipt className="w-5 h-5" />}
            gradient="from-blue-500 to-blue-700"
            shadowColor="shadow-blue-500/25"
            delay={0}
          />
          <ActionTile
            href="/kurye/avans"
            label="Avans"
            sublabel="Talep oluştur"
            icon={<Zap className="w-5 h-5" />}
            gradient="from-amber-500 to-orange-600"
            shadowColor="shadow-amber-500/25"
            delay={50}
          />
          <ActionTile
            href="/kurye/profilim"
            label="Profilim"
            sublabel="Bilgilerim"
            icon={<User className="w-5 h-5" />}
            gradient="from-purple-500 to-purple-700"
            shadowColor="shadow-purple-500/25"
            delay={100}
          />
          <ActionTile
            href="/kurye/talepler"
            label="Taleplerim"
            sublabel={`${stats.pending_count ?? 0} beklemede`}
            icon={<Clock className="w-5 h-5" />}
            gradient="from-emerald-500 to-emerald-700"
            shadowColor="shadow-emerald-500/25"
            delay={150}
            badge={stats.pending_count ?? 0}
          />
        </div>

        {/* Talep istatistikleri */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 mt-4 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <FileText className="w-4 h-4" strokeWidth={2.2} />
              </div>
              <h2 className="font-bold text-slate-900">Talep Durumu</h2>
            </div>
            <Link
              href="/kurye/talepler"
              className="text-xs text-blue-600 hover:text-blue-700 font-semibold inline-flex items-center gap-0.5"
            >
              Tümü <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <StatCard
              label="Beklemede"
              value={stats.pending_count ?? 0}
              accent="amber"
            />
            <StatCard
              label="Onaylandı"
              value={stats.approved_count ?? 0}
              accent="emerald"
            />
            <StatCard
              label="Reddedildi"
              value={stats.rejected_count ?? 0}
              accent="rose"
            />
          </div>
        </div>

        {/* Performans ipucu */}
        <div className="mt-4 mb-6 p-4 bg-gradient-to-br from-blue-600/5 via-purple-500/5 to-blue-600/5 border border-blue-200/40 rounded-2xl animate-fade-in">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 text-white flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/30">
              <TrendingUp className="w-4 h-4" strokeWidth={2.4} />
            </div>
            <div className="flex-1 text-xs leading-relaxed text-slate-700">
              <p className="font-semibold text-slate-900 mb-0.5">İyi gidiyorsun! 💪</p>
              <p>
                Profilini güncel tut, bordrolarını imzalamayı unutma. Her şey
                <strong className="text-blue-700"> tek tıkla </strong>
                avucunda.
              </p>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes hero-in {
          from { opacity: 0; transform: translateY(-12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes card-in {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes stagger-in {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        :global(.animate-hero-in) { animation: hero-in 0.5s ease-out; }
        :global(.animate-card-in) { animation: card-in 0.6s ease-out 0.15s backwards; }
        :global(.animate-stagger-in) { animation: stagger-in 0.6s ease-out 0.3s backwards; }
        :global(.animate-fade-in) { animation: fade-in 0.6s ease-out 0.5s backwards; }
      `}</style>
    </div>
  );
}

// ──────────────────────────────────────────────────────────
// Components
// ──────────────────────────────────────────────────────────

function ActionTile({
  href, label, sublabel, icon, gradient, shadowColor, delay, badge,
}: {
  href: string;
  label: string;
  sublabel: string;
  icon: React.ReactNode;
  gradient: string;
  shadowColor: string;
  delay: number;
  badge?: number;
}) {
  return (
    <Link
      href={href}
      className="group relative bg-white rounded-2xl p-4 shadow-sm border border-slate-100 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 active:scale-[0.98]"
      style={{ animation: `stagger-in 0.5s ease-out ${0.35 + delay / 1000}s backwards` }}
    >
      <div className="flex items-start justify-between mb-3">
        <div
          className={`w-10 h-10 rounded-xl bg-gradient-to-br ${gradient} text-white flex items-center justify-center shadow-md ${shadowColor} group-hover:scale-110 transition-transform`}
        >
          {icon}
        </div>
        {badge !== undefined && badge > 0 && (
          <span className="min-w-[20px] h-5 px-1.5 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center shadow-md shadow-rose-500/30">
            {badge}
          </span>
        )}
      </div>
      <div className="font-bold text-slate-900 text-sm">{label}</div>
      <div className="text-[11px] text-slate-500 mt-0.5">{sublabel}</div>
      <ChevronRight className="absolute top-4 right-4 w-4 h-4 text-slate-300 group-hover:text-slate-500 group-hover:translate-x-0.5 transition-all opacity-0 group-hover:opacity-100" />
    </Link>
  );
}

function StatCard({
  label, value, accent,
}: {
  label: string;
  value: number;
  accent: 'amber' | 'emerald' | 'rose';
}) {
  const colors = {
    amber: { bg: 'bg-amber-50', text: 'text-amber-700', dot: 'bg-amber-500' },
    emerald: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-500' },
    rose: { bg: 'bg-rose-50', text: 'text-rose-700', dot: 'bg-rose-500' },
  };
  const c = colors[accent];

  return (
    <div className={`${c.bg} rounded-xl p-3`}>
      <div className="flex items-center gap-1.5 mb-1">
        <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
        <p className={`text-[10px] font-bold uppercase tracking-wider ${c.text}`}>
          {label}
        </p>
      </div>
      <p className={`font-display text-2xl font-bold ${c.text} tabular-nums`}>
        {value}
      </p>
    </div>
  );
}
