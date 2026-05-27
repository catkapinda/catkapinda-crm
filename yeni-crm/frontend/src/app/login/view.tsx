'use client';

import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';
import {
  AlertCircle, ArrowRight, CheckCircle2, Eye, EyeOff,
  Loader2, Lock, Mail, ShieldCheck,
} from 'lucide-react';

import { forgotPassword, login } from '@/lib/api';

const TR_DAYS = ['Pazar', 'Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi'];
const TR_MONTHS = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                   'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 6) return 'İyi geceler';
  if (h < 12) return 'Günaydın';
  if (h < 18) return 'İyi günler';
  return 'İyi akşamlar';
}

function useLiveTime(): { time: string; date: string } {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  const ss = String(now.getSeconds()).padStart(2, '0');
  const dayName = TR_DAYS[now.getDay()];
  const dayNum = now.getDate();
  const monthName = TR_MONTHS[now.getMonth()];
  const year = now.getFullYear();
  return {
    time: `${hh}:${mm}:${ss}`,
    date: `${dayName}, ${dayNum} ${monthName} ${year}`,
  };
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
  const { time, date } = useLiveTime();

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
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[1.15fr_1fr] relative overflow-hidden">
      {/* ────────── SOL: ATMOSFER ────────── */}
      <aside className="relative hidden lg:flex flex-col p-12 overflow-hidden text-white">
        {/* Gradient background */}
        <div className="absolute inset-0 -z-10">
          <div
            className="absolute inset-0 animate-mesh-shift"
            style={{
              background:
                'radial-gradient(circle at 25% 25%, #1E40AF 0%, transparent 50%), ' +
                'radial-gradient(circle at 75% 75%, #0F52BA 0%, transparent 55%), ' +
                'linear-gradient(135deg, #061735 0%, #0A2A5C 35%, #0F52BA 70%, #1D4ED8 100%)',
            }}
          />
          {/* Floating orbs */}
          <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-cyan-400/15 blur-3xl animate-float-a" />
          <div className="absolute -bottom-40 -left-20 w-[28rem] h-[28rem] rounded-full bg-yellow-400/10 blur-3xl animate-float-b" />
        </div>

        {/* Animated Delivery Network SVG */}
        <DeliveryNetworkSvg />

        {/* Twinkling dots scattered */}
        <Twinkles />

        {/* TOP — Logo + saat */}
        <div className="relative z-10 flex items-center justify-between animate-rise">
          <div className="flex items-center gap-4">
            <div className="relative">
              {/* Glow halo arkaplan */}
              <div className="absolute inset-0 rounded-2xl bg-white/40 blur-xl scale-110" />
              <div className="absolute inset-0 rounded-2xl bg-yellow-200/30 blur-2xl scale-125" />
              {/* Beyaz solid kart */}
              <div className="relative w-16 h-16 rounded-2xl bg-white flex items-center justify-center shadow-[0_8px_30px_rgba(255,255,255,0.35)] ring-2 ring-white/40">
                <Image
                  src="/catkapinda-logo.png"
                  alt="Çat Kapında"
                  width={44}
                  height={44}
                  className="object-contain"
                />
              </div>
            </div>
            <div>
              <div className="text-[26px] font-bold tracking-tight leading-none">
                Çat Kapında
              </div>
              <div className="text-[11px] uppercase tracking-[0.2em] text-white/65 mt-1.5">
                Yönetim Paneli
              </div>
            </div>
          </div>

          {/* Canlı saat */}
          <div className="text-right">
            <div className="font-mono text-[28px] font-bold tracking-tight tabular-nums leading-none">
              {time}
            </div>
            <div className="text-[11px] text-white/60 mt-1.5">
              {date}
            </div>
          </div>
        </div>

        {/* MIDDLE — Brand statement */}
        <div className="relative z-10 flex-1 flex flex-col justify-center max-w-2xl animate-rise delay-200">
          <div className="inline-flex items-center gap-2 text-[11px] font-medium tracking-[0.2em] uppercase text-white/65 mb-5 px-3 py-1.5 rounded-full bg-white/8 border border-white/15 backdrop-blur self-start">
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-300 animate-live-dot" />
            {greeting()}
          </div>
          <h1 className="font-display text-[56px] leading-[0.98] font-bold tracking-tight mb-6">
            Operasyon{' '}
            <span className="relative inline-block">
              <span className="bg-gradient-to-r from-yellow-200 via-amber-200 to-yellow-300 bg-clip-text text-transparent">
                yaşıyor
              </span>
              <svg
                className="absolute -bottom-2 left-0 w-full h-3 text-yellow-300/80"
                viewBox="0 0 200 10"
                preserveAspectRatio="none"
              >
                <path
                  d="M2 5 Q 50 1, 100 5 T 198 5"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
              </svg>
            </span>{' '}
            — siz de canlı bakın.
          </h1>
          <p className="text-[17px] text-white/75 leading-relaxed max-w-xl">
            Restoran, kurye, fatura, hakediş ve tahsilat tek panelde.
            Veri taze, rapor şeffaf, marj KDV uyumlu.
          </p>
        </div>

        {/* BOTTOM — minik footer */}
        <div className="relative z-10 flex items-center justify-between text-[11px] text-white/45 animate-rise delay-400">
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            HTTPS şifreli oturum
          </span>
          <span>© 2026 Çat Kapında</span>
        </div>
      </aside>

      {/* ────────── SAĞ: FORM ────────── */}
      <main className="relative flex items-center justify-center p-6 lg:p-12 bg-gradient-to-br from-cream-50 via-white to-blue-50/40 overflow-hidden">
        <div className="pointer-events-none absolute -top-24 -right-24 w-72 h-72 rounded-full bg-blue-200/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 -left-24 w-72 h-72 rounded-full bg-amber-200/20 blur-3xl" />

        <div className="w-full max-w-md relative">
          {/* Mobile brand */}
          <div className="lg:hidden flex items-center gap-2 mb-6 justify-center animate-rise">
            <Image src="/catkapinda-logo.png" alt="Çat Kapında" width={36} height={36} />
            <div className="font-bold text-text text-lg">Çat Kapında CRM</div>
          </div>

          <div className="bg-white/85 backdrop-blur-xl border border-white shadow-[0_20px_60px_rgba(15,82,186,0.12)] rounded-3xl p-8 animate-rise delay-100">
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
                        <ArrowRight className="w-4 h-4 relative z-10" strokeWidth={2.4} />
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

          <div className="text-center mt-5 text-[10.5px] text-text-3 animate-rise delay-200">
            v3 Premium · {new Date().getFullYear()}
          </div>
        </div>
      </main>
    </div>
  );
}

// ────────── Decorative components ──────────

function DeliveryNetworkSvg() {
  // Statik 5 düğüm noktası + onları bağlayan yollar
  // Her path kendi süresinde çizilip silinerek tekrarlanır
  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none opacity-50"
      viewBox="0 0 700 700"
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <linearGradient id="route" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FCD34D" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#7DD3FC" stopOpacity="0.4" />
        </linearGradient>
        <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" />
          <feMerge>
            <feMergeNode />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Yollar (animated path-draw) */}
      <path
        d="M 100 150 Q 250 80, 400 200 T 600 300"
        fill="none"
        stroke="url(#route)"
        strokeWidth="1.6"
        strokeDasharray="800"
        style={{
          ['--len' as string]: '800',
          animation: 'path-draw 9s ease-in-out infinite',
        }}
      />
      <path
        d="M 600 300 Q 500 450, 300 500 T 80 580"
        fill="none"
        stroke="url(#route)"
        strokeWidth="1.6"
        strokeDasharray="800"
        style={{
          ['--len' as string]: '800',
          animation: 'path-draw 11s ease-in-out infinite',
          animationDelay: '2s',
        }}
      />
      <path
        d="M 100 150 Q 200 350, 380 380 T 620 540"
        fill="none"
        stroke="url(#route)"
        strokeWidth="1.6"
        strokeDasharray="800"
        style={{
          ['--len' as string]: '800',
          animation: 'path-draw 13s ease-in-out infinite',
          animationDelay: '4s',
        }}
      />
      <path
        d="M 80 580 Q 220 480, 420 400 T 600 300"
        fill="none"
        stroke="url(#route)"
        strokeWidth="1.2"
        strokeDasharray="800"
        opacity="0.5"
        style={{
          ['--len' as string]: '800',
          animation: 'path-draw 15s ease-in-out infinite',
          animationDelay: '1s',
        }}
      />

      {/* Düğüm noktaları */}
      {[
        { cx: 100, cy: 150, delay: '0s' },
        { cx: 600, cy: 300, delay: '0.5s' },
        { cx: 80, cy: 580, delay: '1s' },
        { cx: 380, cy: 380, delay: '1.5s' },
        { cx: 620, cy: 540, delay: '2s' },
      ].map((n, i) => (
        <g key={i}>
          <circle
            cx={n.cx} cy={n.cy} r="4"
            fill="#FCD34D"
            filter="url(#glow)"
            style={{
              animation: 'pulse-node 2.5s ease-in-out infinite',
              animationDelay: n.delay,
            }}
          />
          <circle
            cx={n.cx} cy={n.cy} r="10"
            fill="none"
            stroke="#FCD34D"
            strokeWidth="1"
            opacity="0.4"
            style={{
              animation: 'pulse-node 2.5s ease-in-out infinite',
              animationDelay: n.delay,
            }}
          />
        </g>
      ))}
    </svg>
  );
}

function Twinkles() {
  // Random konumlarda parıltılı yıldız noktaları
  const stars = [
    { top: '12%', left: '18%', delay: '0s' },
    { top: '28%', left: '72%', delay: '0.8s' },
    { top: '55%', left: '15%', delay: '1.6s' },
    { top: '70%', left: '85%', delay: '0.4s' },
    { top: '85%', left: '40%', delay: '2.2s' },
    { top: '40%', left: '55%', delay: '1.2s' },
    { top: '18%', left: '88%', delay: '2.8s' },
  ];
  return (
    <div className="absolute inset-0 pointer-events-none">
      {stars.map((s, i) => (
        <div
          key={i}
          className="absolute w-1 h-1 rounded-full bg-white animate-twinkle"
          style={{ top: s.top, left: s.left, animationDelay: s.delay }}
        />
      ))}
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
