'use client';

import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
import {
  AlertCircle, ArrowRight, Bike, CheckCircle2, Eye, EyeOff,
  Loader2, Lock, Mail, Package, Receipt, ShieldCheck, Sparkles,
  Store, TrendingUp, Users, Zap,
} from 'lucide-react';

import { forgotPassword, login } from '@/lib/api';

// Time-based greeting
function greeting(): string {
  const h = new Date().getHours();
  if (h < 6) return 'İyi geceler';
  if (h < 12) return 'Günaydın';
  if (h < 18) return 'İyi günler';
  return 'İyi akşamlar';
}

// Rotating taglines
const TAGLINES = [
  'Tek panelden uçtan uca operasyon.',
  'Dedike kurye, dinamik fatura, gerçek zamanlı görünüm.',
  'Mart\'tan beri 25 restoran, 80+ kurye, 50K+ paket.',
  'AI destekli rapor, KDV uyumlu marj, açık kapı şeffaflık.',
];

function useCounter(target: number, durationMs = 1400): number {
  const [value, setValue] = useState(0);
  const startedRef = useRef(false);
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / durationMs);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);
  return value;
}

export function LoginView({ nextUrl }: { nextUrl: string }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<'login' | 'forgot'>('login');
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSent, setForgotSent] = useState(false);
  const [taglineIdx, setTaglineIdx] = useState(0);

  // Rotate taglines
  useEffect(() => {
    const id = setInterval(() => setTaglineIdx((i) => (i + 1) % TAGLINES.length), 4500);
    return () => clearInterval(id);
  }, []);

  const restaurantCount = useCounter(25);
  const courierCount = useCounter(80);
  const packagesCount = useCounter(52000);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) { setError('E-posta ve parola gerekli.'); return; }
    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      window.location.href = nextUrl && nextUrl !== '/login' ? nextUrl : '/';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Giriş başarısız');
      setLoading(false);
    }
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault();
    if (!forgotEmail) { setError('E-posta gerekli.'); return; }
    setLoading(true);
    setError(null);
    try {
      await forgotPassword(forgotEmail.trim());
      setForgotSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'İstek başarısız');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] relative overflow-hidden">
      {/* ────────── SOL: MARKA + ANİMASYON ────────── */}
      <aside className="relative hidden lg:flex flex-col justify-between p-12 overflow-hidden text-white">
        {/* Animated mesh gradient background */}
        <div className="absolute inset-0 -z-10">
          <div
            className="absolute inset-0 animate-mesh-shift"
            style={{
              background:
                'radial-gradient(circle at 20% 30%, #1E40AF 0%, transparent 50%), ' +
                'radial-gradient(circle at 80% 70%, #0F52BA 0%, transparent 55%), ' +
                'linear-gradient(135deg, #0A2A5C 0%, #0F52BA 50%, #1D4ED8 100%)',
            }}
          />
          {/* Pattern overlay */}
          <div
            className="absolute inset-0 opacity-[0.07] animate-grid-drift"
            style={{
              backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />
          {/* Floating orbs */}
          <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-cyan-400/20 blur-3xl animate-float-a" />
          <div className="absolute -bottom-40 -left-20 w-[28rem] h-[28rem] rounded-full bg-yellow-400/15 blur-3xl animate-float-b" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 rounded-full bg-blue-300/10 blur-3xl animate-float-a" />
        </div>

        {/* Logo + Live indicator */}
        <div className="relative flex items-center justify-between animate-rise">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-white/15 backdrop-blur border border-white/25 flex items-center justify-center shadow-lg">
              <Image
                src="/catkapinda-logo.png"
                alt="Çat Kapında"
                width={32}
                height={32}
                className="object-contain"
              />
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-[0.2em] text-white/70">
                CRM Sistem v3
              </div>
              <div className="text-xl font-bold tracking-tight">
                Çat Kapında
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur border border-white/20">
            <span className="w-2 h-2 rounded-full bg-yellow-300 animate-live-dot" />
            <span className="text-[10.5px] font-bold uppercase tracking-wider text-yellow-200">
              Sistem aktif
            </span>
          </div>
        </div>

        {/* Headline + tanıtım */}
        <div className="relative space-y-7 max-w-xl">
          <div className="animate-rise delay-100">
            <div className="inline-flex items-center gap-2 text-[11px] font-medium tracking-[0.2em] uppercase text-white/70 mb-4 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 backdrop-blur">
              <Sparkles className="w-3 h-3 text-yellow-300" strokeWidth={2.4} />
              Dedike Kurye CRM · {greeting()}!
            </div>
            <h1 className="font-display text-[44px] leading-[1.05] font-bold tracking-tight mb-4">
              Operasyonunu{' '}
              <span className="relative inline-block">
                <span className="bg-gradient-to-r from-yellow-300 via-amber-200 to-yellow-300 bg-clip-text text-transparent">
                  tek panelden
                </span>
                <span className="absolute -bottom-1 left-0 right-0 h-[3px] bg-gradient-to-r from-yellow-300 to-transparent rounded-full" />
              </span>{' '}
              yönet.
            </h1>
            <div className="h-7 relative overflow-hidden">
              {TAGLINES.map((t, i) => (
                <p
                  key={i}
                  className="absolute inset-0 text-[15px] text-white/80 leading-relaxed transition-all duration-500"
                  style={{
                    opacity: i === taglineIdx ? 1 : 0,
                    transform: `translateY(${i === taglineIdx ? 0 : 12}px)`,
                  }}
                >
                  {t}
                </p>
              ))}
            </div>
          </div>

          {/* Stat counters */}
          <div className="grid grid-cols-3 gap-3 animate-rise delay-200">
            <StatBlock icon={<Store className="w-4 h-4" />} value={restaurantCount} label="Restoran" />
            <StatBlock icon={<Bike className="w-4 h-4" />} value={courierCount} label="Kurye" />
            <StatBlock icon={<Package className="w-4 h-4" />} value={packagesCount} label="Paket / ay" big />
          </div>

          {/* Feature pills */}
          <div className="grid grid-cols-2 gap-2.5 animate-rise delay-300">
            <FeaturePill icon={<Users className="w-3.5 h-3.5" />} text="Puantaj + Hakediş" />
            <FeaturePill icon={<Receipt className="w-3.5 h-3.5" />} text="Fatura + Tahsilat" />
            <FeaturePill icon={<TrendingUp className="w-3.5 h-3.5" />} text="Kâr-Zarar + Marj" />
            <FeaturePill icon={<Sparkles className="w-3.5 h-3.5" />} text="AI İçgörü + Veri Sağlığı" />
          </div>
        </div>

        {/* Footer */}
        <div className="relative animate-rise delay-400">
          <div className="text-[11px] text-white/55 flex items-center gap-2">
            <ShieldCheck className="w-3.5 h-3.5" />
            HTTPS güvenli oturum · Veriler Çat Kapında özel altyapısında
          </div>
          <div className="text-[10.5px] text-white/40 mt-1.5">
            © 2026 Çat Kapında · Tüm hakları saklıdır
          </div>
        </div>

        {/* Orbiting icons — decoration */}
        <div className="pointer-events-none absolute top-1/2 right-12 w-2 h-2">
          <div className="absolute w-8 h-8 -top-4 -left-4 rounded-full bg-white/10 backdrop-blur border border-white/20 flex items-center justify-center animate-orbit-slow">
            <Package className="w-3 h-3 text-white" />
          </div>
          <div className="absolute w-8 h-8 -top-4 -left-4 rounded-full bg-white/10 backdrop-blur border border-white/20 flex items-center justify-center animate-orbit-mid">
            <Bike className="w-3 h-3 text-yellow-200" />
          </div>
          <div className="absolute w-8 h-8 -top-4 -left-4 rounded-full bg-white/10 backdrop-blur border border-white/20 flex items-center justify-center animate-orbit-fast">
            <Zap className="w-3 h-3 text-cyan-200" />
          </div>
        </div>
      </aside>

      {/* ────────── SAĞ: FORM ────────── */}
      <main className="relative flex items-center justify-center p-6 lg:p-12 bg-gradient-to-br from-cream-50 via-white to-blue-50/40 overflow-hidden">
        {/* Subtle background decoration */}
        <div className="pointer-events-none absolute -top-24 -right-24 w-72 h-72 rounded-full bg-blue-200/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 -left-24 w-72 h-72 rounded-full bg-amber-200/20 blur-3xl" />

        <div className="w-full max-w-md relative">
          {/* Mobile brand */}
          <div className="lg:hidden flex items-center gap-2 mb-6 justify-center animate-rise">
            <Image src="/catkapinda-logo.png" alt="Çat Kapında" width={36} height={36} />
            <div className="font-bold text-text text-lg">Çat Kapında CRM</div>
          </div>

          {/* Card */}
          <div className="bg-white/80 backdrop-blur-xl border border-white shadow-[0_20px_60px_rgba(15,82,186,0.12)] rounded-3xl p-8 animate-rise delay-100">
            {mode === 'login' ? (
              <>
                <div className="mb-6">
                  <h2 className="font-display text-[32px] font-bold tracking-tight text-text mb-1 leading-none">
                    Hoş geldiniz
                  </h2>
                  <p className="text-text-3 text-sm">
                    Devam etmek için giriş yapın
                  </p>
                </div>

                <form onSubmit={handleLogin} className="space-y-4">
                  <Field
                    icon={<Mail className="w-4 h-4" />}
                    type="email"
                    label="E-posta"
                    placeholder="ornek@catkapinda.com"
                    value={email}
                    onChange={setEmail}
                    autoFocus
                    required
                  />

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="block text-[11.5px] font-bold text-text-2 uppercase tracking-wider">
                        Parola
                      </label>
                      <button
                        type="button"
                        onClick={() => { setMode('forgot'); setError(null); }}
                        className="text-[11px] text-brand hover:text-brand-dark hover:underline font-semibold transition"
                      >
                        Şifremi unuttum?
                      </button>
                    </div>
                    <div className="relative group">
                      <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-3 group-focus-within:text-brand transition" strokeWidth={2.2} />
                      <input
                        type={showPwd ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        placeholder="••••••••"
                        className="w-full pl-10 pr-10 py-3.5 rounded-xl border border-border text-sm focus:outline-none focus:border-brand focus:ring-4 focus:ring-brand/15 transition-all bg-white"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPwd((v) => !v)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-text-3 hover:text-brand transition p-1"
                      >
                        {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-[12.5px] flex items-start gap-2 animate-rise">
                      <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading}
                    className="relative w-full py-3.5 rounded-xl bg-gradient-to-r from-brand-dark via-brand to-blue-600 text-white font-bold text-sm shadow-lg shadow-brand/30 hover:shadow-xl hover:shadow-brand/40 hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-60 disabled:cursor-wait inline-flex items-center justify-center gap-2 overflow-hidden animate-btn-shimmer"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <span className="relative z-10">Giriş Yap</span>
                        <ArrowRight className="w-4 h-4 relative z-10 group-hover:translate-x-1 transition" strokeWidth={2.4} />
                      </>
                    )}
                  </button>
                </form>

                <div className="mt-7 pt-5 border-t border-border/60 text-center">
                  <div className="text-[11px] text-text-3 mb-2">
                    Erişim sorununuz mu var?
                  </div>
                  <div className="text-[11.5px] text-text-2 font-medium">
                    Sistem yöneticisi: <span className="text-brand">info@catkapinda.com</span>
                  </div>
                </div>
              </>
            ) : (
              // ─── ŞİFREMİ UNUTTUM ───
              <>
                <div className="mb-6">
                  <button
                    type="button"
                    onClick={() => { setMode('login'); setError(null); setForgotSent(false); }}
                    className="text-[11px] text-text-3 hover:text-brand font-semibold mb-3 inline-flex items-center gap-1 transition"
                  >
                    ← Girişe dön
                  </button>
                  <h2 className="font-display text-[32px] font-bold tracking-tight text-text mb-1 leading-none">
                    Şifre Sıfırlama
                  </h2>
                  <p className="text-text-3 text-sm">
                    E-postanıza sıfırlama linki gönderilir
                  </p>
                </div>

                {forgotSent ? (
                  <div className="bg-gradient-to-br from-emerald-50 to-emerald-100/50 border border-emerald-200 rounded-2xl p-5 animate-rise">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center flex-shrink-0">
                        <CheckCircle2 className="w-5 h-5 text-emerald-600" strokeWidth={2.4} />
                      </div>
                      <div>
                        <div className="font-bold text-emerald-800 mb-1">
                          İstek alındı
                        </div>
                        <p className="text-[12.5px] text-emerald-700 leading-relaxed">
                          <strong className="text-emerald-900">{forgotEmail}</strong> sistemde kayıtlıysa
                          sıfırlama linki gönderildi. Spam klasörünü de kontrol edin.
                          Link 24 saat geçerli.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleForgot} className="space-y-4">
                    <Field
                      icon={<Mail className="w-4 h-4" />}
                      type="email"
                      label="E-posta"
                      placeholder="ornek@catkapinda.com"
                      value={forgotEmail}
                      onChange={setForgotEmail}
                      autoFocus
                      required
                    />

                    {error && (
                      <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-[12.5px] flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                        <span>{error}</span>
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={loading}
                      className="relative w-full py-3.5 rounded-xl bg-gradient-to-r from-brand-dark via-brand to-blue-600 text-white font-bold text-sm shadow-lg shadow-brand/30 hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60 inline-flex items-center justify-center gap-2 overflow-hidden animate-btn-shimmer"
                    >
                      {loading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <>Sıfırlama Linki Gönder <ArrowRight className="w-4 h-4" strokeWidth={2.4} /></>
                      )}
                    </button>
                  </form>
                )}
              </>
            )}
          </div>

          {/* Sub footer */}
          <div className="text-center mt-5 text-[10.5px] text-text-3 animate-rise delay-200">
            v3 Premium · Build {new Date().getFullYear()}
          </div>
        </div>
      </main>
    </div>
  );
}

// ────────── Yardımcı componentler ──────────

function StatBlock({
  icon, value, label, big,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
  big?: boolean;
}) {
  return (
    <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-3.5 hover:bg-white/15 transition">
      <div className="flex items-center gap-1.5 mb-2">
        <span className="w-6 h-6 rounded-lg bg-white/20 flex items-center justify-center text-yellow-200">
          {icon}
        </span>
      </div>
      <div className={`font-display font-bold tracking-tight leading-none tabular-nums ${big ? 'text-[26px]' : 'text-[22px]'}`}>
        {value.toLocaleString('tr-TR')}<span className="text-yellow-300">+</span>
      </div>
      <div className="text-[10.5px] text-white/65 mt-1 font-medium">{label}</div>
    </div>
  );
}

function FeaturePill({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white/8 backdrop-blur border border-white/15 hover:bg-white/15 transition group">
      <span className="text-yellow-200 group-hover:scale-110 transition-transform">{icon}</span>
      <span className="text-[11.5px] font-semibold text-white/90">{text}</span>
    </div>
  );
}

function Field({
  icon, type, label, placeholder, value, onChange, autoFocus, required,
}: {
  icon: React.ReactNode;
  type: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
  autoFocus?: boolean;
  required?: boolean;
}) {
  return (
    <div>
      <label className="block text-[11.5px] font-bold text-text-2 uppercase tracking-wider mb-1.5">
        {label}
      </label>
      <div className="relative group">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-3 group-focus-within:text-brand transition">
          {icon}
        </span>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoFocus={autoFocus}
          required={required}
          className="w-full pl-10 pr-3 py-3.5 rounded-xl border border-border text-sm focus:outline-none focus:border-brand focus:ring-4 focus:ring-brand/15 transition-all bg-white"
        />
      </div>
    </div>
  );
}
