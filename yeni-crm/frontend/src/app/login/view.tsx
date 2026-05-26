'use client';

import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import {
  AlertCircle, ArrowRight, BarChart3, CheckCircle2, Eye, EyeOff,
  Loader2, Lock, Mail, Receipt, Sparkles, ShieldCheck, Users,
} from 'lucide-react';

import { forgotPassword, login } from '@/lib/api';

export function LoginView({ nextUrl }: { nextUrl: string }) {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<'login' | 'forgot'>('login');
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSent, setForgotSent] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) {
      setError('E-posta ve parola gerekli.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      // Sayfayı tamamen yenile ki middleware cookie'yi görebilsin
      window.location.href = nextUrl && nextUrl !== '/login' ? nextUrl : '/';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Giriş başarısız');
      setLoading(false);
    }
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault();
    if (!forgotEmail) {
      setError('E-posta gerekli.');
      return;
    }
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
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-[1.05fr_1fr]">
      {/* ────────── SOL: Marka & özet ────────── */}
      <aside className="relative hidden lg:flex flex-col justify-between p-12 overflow-hidden text-white">
        <div className="absolute inset-0 -z-10">
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
              backgroundImage:
                'radial-gradient(circle, white 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />
        </div>

        {/* Logo */}
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
              CRM Sistem
            </div>
            <div className="text-xl font-bold tracking-tight">
              Çat Kapında
            </div>
          </div>
        </div>

        {/* Tanıtım */}
        <div className="space-y-6 max-w-xl">
          <div>
            <div className="inline-flex items-center gap-2 text-[11px] font-medium tracking-[0.2em] uppercase text-white/70 mb-3">
              <span className="inline-block w-2 h-2 rounded-full bg-yellow-300 animate-pulse" />
              Dedike Kurye Operasyonu için CRM
            </div>
            <h1 className="text-4xl font-bold leading-tight tracking-tight mb-3">
              Restoran ve kurye operasyonunu tek panelden yönet.
            </h1>
            <p className="text-white/80 text-[15px] leading-relaxed">
              Çat Kapında CRM — puantajdan bordroya, restoran faturasından
              tahsilatına, AI destekli raporlardan kurye hareket takibine
              kadar tüm operasyonu uçtan uca yönetir.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Feature icon={<Users className="w-4 h-4" />} title="Personel & Puantaj" desc="Kurye, joker, yönetim — aylık vardiya ve hakediş" />
            <Feature icon={<Receipt className="w-4 h-4" />} title="Fatura & Tahsilat" desc="Pricing model'e göre otomatik fatura, KDV uyumlu" />
            <Feature icon={<BarChart3 className="w-4 h-4" />} title="Restoran Raporları" desc="Turnover, verim, paket başı maliyet, AI yorumu" />
            <Feature icon={<Sparkles className="w-4 h-4" />} title="Kâr-Zarar & İçgörü" desc="Aylık marj, anomali tespiti, sağlık paneli" />
          </div>
        </div>

        <div className="text-[11.5px] text-white/55 flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5" />
          Tüm bağlantılar güvenli (HTTPS) — verileriniz Çat Kapında özelinde tutulur.
        </div>
      </aside>

      {/* ────────── SAĞ: Form ────────── */}
      <main className="flex items-center justify-center p-6 lg:p-12 bg-cream-50/40">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-6 justify-center">
            <Image
              src="/catkapinda-logo.png"
              alt="Çat Kapında"
              width={36}
              height={36}
              className="object-contain"
            />
            <div className="font-bold text-text text-lg">Çat Kapında CRM</div>
          </div>

          {mode === 'login' ? (
            <>
              <div className="mb-7">
                <h2 className="font-display text-3xl font-bold tracking-tight text-text mb-1">
                  Hoş geldiniz
                </h2>
                <p className="text-text-3 text-sm">
                  Hesabınıza giriş yapın
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
                      className="text-[11px] text-brand hover:underline font-semibold"
                    >
                      Şifremi unuttum?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-3" strokeWidth={2.2} />
                    <input
                      type={showPwd ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      placeholder="••••••••"
                      className="w-full pl-10 pr-10 py-3 rounded-xl border border-border text-sm focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwd((v) => !v)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-3 hover:text-text-2 transition"
                    >
                      {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-[12.5px] flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-brand-dark to-brand text-white font-bold text-sm shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60 disabled:cursor-wait inline-flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      Giriş Yap <ArrowRight className="w-4 h-4" strokeWidth={2.4} />
                    </>
                  )}
                </button>
              </form>

              <div className="mt-8 text-center text-[11px] text-text-3">
                Erişim sorunu mu yaşıyorsunuz? Sistem yöneticinizle iletişime geçin.
              </div>
            </>
          ) : (
            // ─── ŞİFREMİ UNUTTUM ───
            <>
              <div className="mb-7">
                <h2 className="font-display text-3xl font-bold tracking-tight text-text mb-1">
                  Şifre Sıfırlama
                </h2>
                <p className="text-text-3 text-sm">
                  E-posta adresinize sıfırlama linki gönderilir
                </p>
              </div>

              {forgotSent ? (
                <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold text-emerald-800 mb-1">
                        İstek alındı
                      </div>
                      <p className="text-[13px] text-emerald-700 leading-relaxed">
                        Eğer <strong>{forgotEmail}</strong> sistemde kayıtlıysa, kısa süre içinde
                        bir sıfırlama linki gönderilecek. Spam klasörünüzü de kontrol edin.
                        Link 24 saat geçerli.
                      </p>
                      <button
                        onClick={() => {
                          setMode('login');
                          setForgotSent(false);
                          setForgotEmail('');
                          setError(null);
                        }}
                        className="mt-3 text-[12px] text-brand font-semibold hover:underline inline-flex items-center gap-1"
                      >
                        ← Girişe dön
                      </button>
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
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-brand-dark to-brand text-white font-bold text-sm shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60 inline-flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <>Sıfırlama Linki Gönder <ArrowRight className="w-4 h-4" strokeWidth={2.4} /></>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => { setMode('login'); setError(null); }}
                    className="w-full text-[12px] text-text-3 hover:text-brand transition font-semibold"
                  >
                    ← Girişe dön
                  </button>
                </form>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}

function Feature({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="bg-white/10 backdrop-blur-sm border border-white/15 rounded-xl p-3.5 hover:bg-white/15 transition">
      <div className="flex items-center gap-2 mb-1">
        <span className="w-6 h-6 rounded-lg bg-white/15 flex items-center justify-center">
          {icon}
        </span>
        <div className="text-[12.5px] font-bold text-white">{title}</div>
      </div>
      <div className="text-[11px] text-white/70 leading-relaxed">{desc}</div>
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
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-3">{icon}</span>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoFocus={autoFocus}
          required={required}
          className="w-full pl-10 pr-3 py-3 rounded-xl border border-border text-sm focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
        />
      </div>
    </div>
  );
}
