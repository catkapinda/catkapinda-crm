'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle, ArrowLeft, ArrowRight, KeyRound,
  Loader2, Phone, Shield, Sparkles,
} from 'lucide-react';

import { requestLoginOtp, verifyLoginOtp } from '@/lib/courier-api';

type Step = 'phone' | 'otp' | 'fallback';

export default function CourierLoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('phone');

  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [maskedPhone, setMaskedPhone] = useState('');
  const [resendIn, setResendIn] = useState(0);

  const [personCode, setPersonCode] = useState('');
  const [last4Tc, setLast4Tc] = useState('');

  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // 6 ayrı OTP kutusu için ref'ler
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (step === 'otp' && otpRefs.current[0]) {
      otpRefs.current[0]?.focus();
    }
  }, [step]);

  useEffect(() => {
    if (resendIn <= 0) return;
    const id = setInterval(() => setResendIn((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [resendIn]);

  // Telefonu formatlanmış (0 5XX XXX XX XX) göster
  const formatPhone = (raw: string) => {
    const digits = raw.replace(/\D/g, '').slice(0, 11);
    if (digits.length === 0) return '';
    if (digits.length <= 1) return digits;
    if (digits.length <= 4) return `${digits.slice(0, 1)} ${digits.slice(1)}`;
    if (digits.length <= 7) return `${digits.slice(0, 1)} ${digits.slice(1, 4)} ${digits.slice(4)}`;
    if (digits.length <= 9) return `${digits.slice(0, 1)} ${digits.slice(1, 4)} ${digits.slice(4, 7)} ${digits.slice(7)}`;
    return `${digits.slice(0, 1)} ${digits.slice(1, 4)} ${digits.slice(4, 7)} ${digits.slice(7, 9)} ${digits.slice(9, 11)}`;
  };

  const handleRequestOtp = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError('');
    setBusy(true);
    try {
      const result = await requestLoginOtp(phone);
      setMaskedPhone(result.masked_phone);
      setResendIn(result.cooldown_seconds || 60);
      setOtp('');
      setStep('otp');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kod gönderilemedi');
    } finally {
      setBusy(false);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const newOtp = otp.split('');
    while (newOtp.length < 6) newOtp.push('');
    newOtp[index] = digit;
    const next = newOtp.join('').slice(0, 6);
    setOtp(next);
    setError('');

    // Sonraki kutucuğa fokuslan
    if (digit && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }

    // 6. dijit girilince otomatik gönder
    if (next.length === 6 && index === 5) {
      submitOtp(next);
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
    if (e.key === 'ArrowLeft' && index > 0) {
      otpRefs.current[index - 1]?.focus();
    }
    if (e.key === 'ArrowRight' && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!text) return;
    setOtp(text);
    if (text.length === 6) submitOtp(text);
    else otpRefs.current[Math.min(text.length, 5)]?.focus();
  };

  const submitOtp = async (code: string) => {
    if (code.length !== 6) return;
    setError('');
    setBusy(true);
    try {
      const result = await verifyLoginOtp(phone, code);
      localStorage.setItem('courier_token', result.token);
      router.push('/kurye/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kod doğrulanamadı');
      setOtp('');
      setBusy(false);
      otpRefs.current[0]?.focus();
    }
  };

  const handleResend = async () => {
    if (resendIn > 0 || busy) return;
    setError('');
    setBusy(true);
    try {
      const result = await requestLoginOtp(phone);
      setResendIn(result.cooldown_seconds || 60);
      setOtp('');
      otpRefs.current[0]?.focus();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kod gönderilemedi');
    } finally {
      setBusy(false);
    }
  };

  const handleFallbackLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const res = await fetch('/api/courier/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          person_code: personCode.toUpperCase(),
          last4_tc: last4Tc,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || 'Giriş başarısız');
        return;
      }
      const data = await res.json();
      localStorage.setItem('courier_token', data.token);
      router.push('/kurye/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sunucu hatası');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Animated background orbs */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      {/* Subtle dot pattern */}
      <div
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* Main content */}
      <div className="relative min-h-screen flex flex-col items-center justify-center px-5 py-10">
        <div className="w-full max-w-sm">
          {/* Brand */}
          <div className="text-center mb-8 animate-fade-in-down">
            <div className="inline-block mb-3 relative">
              <div className="absolute inset-0 blur-2xl bg-blue-400/30 rounded-full scale-110" />
              <div className="relative w-24 h-24 mx-auto rounded-3xl bg-gradient-to-br from-white/15 to-white/5 backdrop-blur-xl border border-white/30 shadow-2xl flex items-center justify-center overflow-hidden">
                {/* Stylized "Ç" logomark — fallback as image */}
                <img
                  src="/catkapinda-logo.png?v=3"
                  alt=""
                  className="absolute inset-2 w-[calc(100%-1rem)] h-[calc(100%-1rem)] object-contain drop-shadow-lg z-10"
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                />
                {/* Background fallback letter — visible if logo fails */}
                <span className="font-display font-bold text-5xl text-white/95 drop-shadow-lg">
                  Ç
                </span>
              </div>
            </div>
            <h1 className="font-display text-2xl font-bold text-white tracking-tight">
              Çat Kapında
            </h1>
            <p className="text-blue-100/70 text-sm mt-1 font-medium">
              Kurye Portalı
            </p>
          </div>

          {/* Card */}
          <div className="relative animate-fade-in-up">
            {/* Card glow */}
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-400/20 via-cyan-300/20 to-blue-400/20 rounded-3xl blur-xl opacity-50" />

            <div className="relative bg-white/95 backdrop-blur-2xl rounded-3xl shadow-2xl border border-white/40 overflow-hidden">
              {step === 'phone' && (
                <form onSubmit={handleRequestOtp} className="p-7 space-y-5 animate-step-in">
                  <div className="flex items-start gap-3">
                    <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-700 text-white flex items-center justify-center flex-shrink-0 shadow-lg shadow-blue-500/30">
                      <Phone className="w-5 h-5" strokeWidth={2.2} />
                    </div>
                    <div className="flex-1">
                      <h2 className="font-bold text-slate-900 text-lg">Telefon Numaran</h2>
                      <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                        Kayıtlı numarana 6 haneli kod göndereceğiz
                      </p>
                    </div>
                  </div>

                  {error && (
                    <div className="animate-shake p-3 bg-red-50 border border-red-200 rounded-xl flex gap-2 items-start">
                      <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-red-700 leading-relaxed">{error}</p>
                    </div>
                  )}

                  <div className="relative">
                    <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 font-mono pointer-events-none">
                      📱
                    </div>
                    <input
                      type="tel"
                      inputMode="tel"
                      autoComplete="tel"
                      placeholder="0 5__ ___ __ __"
                      value={formatPhone(phone)}
                      onChange={(e) => {
                        setPhone(e.target.value.replace(/\D/g, ''));
                        setError('');
                      }}
                      disabled={busy}
                      className="w-full pl-12 pr-4 py-4 text-lg font-mono font-semibold bg-slate-50 border-2 border-slate-200 rounded-2xl focus:outline-none focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10 transition-all duration-200 disabled:opacity-50"
                      required
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={busy || phone.length < 10}
                    className="group relative w-full py-4 px-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-2xl font-bold text-base hover:shadow-xl hover:shadow-blue-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 hover:-translate-y-0.5 overflow-hidden"
                  >
                    <span className="relative z-10 inline-flex items-center justify-center gap-2">
                      {busy ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" /> Kod gönderiliyor...
                        </>
                      ) : (
                        <>
                          Kod Gönder <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </>
                      )}
                    </span>
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-700 to-blue-800 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>

                  <button
                    type="button"
                    onClick={() => setStep('fallback')}
                    disabled={busy}
                    className="w-full text-xs text-slate-500 hover:text-slate-700 underline-offset-2 hover:underline pt-1 disabled:opacity-50 transition-colors"
                  >
                    SMS gelmiyor mu? Personel kodu ile gir
                  </button>
                </form>
              )}

              {step === 'otp' && (
                <div className="p-7 space-y-5 animate-step-in">
                  <button
                    type="button"
                    onClick={() => {
                      setStep('phone');
                      setOtp('');
                      setError('');
                    }}
                    disabled={busy}
                    className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-900 disabled:opacity-50 transition-colors"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" /> Numara değiştir
                  </button>

                  <div className="flex items-start gap-3">
                    <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 text-white flex items-center justify-center flex-shrink-0 shadow-lg shadow-emerald-500/30">
                      <KeyRound className="w-5 h-5" strokeWidth={2.2} />
                    </div>
                    <div className="flex-1">
                      <h2 className="font-bold text-slate-900 text-lg">Doğrulama Kodu</h2>
                      <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                        <span className="font-mono font-semibold text-slate-700">
                          {maskedPhone}
                        </span>{' '}
                        numarasına gönderildi
                      </p>
                    </div>
                  </div>

                  {error && (
                    <div className="animate-shake p-3 bg-red-50 border border-red-200 rounded-xl flex gap-2 items-start">
                      <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-red-700 leading-relaxed">{error}</p>
                    </div>
                  )}

                  {/* 6 ayrı OTP kutusu */}
                  <div className="flex justify-between gap-2" onPaste={handleOtpPaste}>
                    {Array.from({ length: 6 }).map((_, i) => (
                      <input
                        key={i}
                        ref={(el) => { otpRefs.current[i] = el; }}
                        type="tel"
                        inputMode="numeric"
                        autoComplete={i === 0 ? 'one-time-code' : 'off'}
                        maxLength={1}
                        value={otp[i] || ''}
                        onChange={(e) => handleOtpChange(i, e.target.value)}
                        onKeyDown={(e) => handleOtpKeyDown(i, e)}
                        disabled={busy}
                        className={`w-full aspect-square text-center text-2xl font-mono font-bold border-2 rounded-2xl transition-all duration-200 disabled:opacity-50 ${
                          otp[i]
                            ? 'border-blue-500 bg-blue-50 text-blue-900 shadow-md shadow-blue-500/20'
                            : 'border-slate-200 bg-slate-50 text-slate-900 focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-500/10'
                        } focus:outline-none`}
                        placeholder="•"
                      />
                    ))}
                  </div>

                  {busy && (
                    <div className="flex items-center justify-center gap-2 text-emerald-700">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm font-medium">Doğrulanıyor...</span>
                    </div>
                  )}

                  <div className="text-center pt-1">
                    {resendIn > 0 ? (
                      <p className="text-xs text-slate-500">
                        Yeniden gönderim için <strong className="text-slate-700">{resendIn}s</strong> bekle
                      </p>
                    ) : (
                      <button
                        type="button"
                        onClick={handleResend}
                        disabled={busy}
                        className="text-xs text-blue-600 hover:text-blue-800 font-semibold underline-offset-2 hover:underline disabled:opacity-50 transition-colors"
                      >
                        Kodu yeniden gönder
                      </button>
                    )}
                  </div>
                </div>
              )}

              {step === 'fallback' && (
                <form onSubmit={handleFallbackLogin} className="p-7 space-y-5 animate-step-in">
                  <button
                    type="button"
                    onClick={() => {
                      setStep('phone');
                      setError('');
                    }}
                    disabled={busy}
                    className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-900 disabled:opacity-50 transition-colors"
                  >
                    <ArrowLeft className="w-3.5 h-3.5" /> SMS ile gir
                  </button>

                  <div className="flex items-start gap-3">
                    <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 text-white flex items-center justify-center flex-shrink-0 shadow-lg shadow-amber-500/30">
                      <Shield className="w-5 h-5" strokeWidth={2.2} />
                    </div>
                    <div className="flex-1">
                      <h2 className="font-bold text-slate-900 text-lg">Personel Kodu ile Giriş</h2>
                      <p className="text-xs text-slate-500 mt-0.5">
                        SMS alamıyorsan bu yöntemi kullan
                      </p>
                    </div>
                  </div>

                  {error && (
                    <div className="animate-shake p-3 bg-red-50 border border-red-200 rounded-xl flex gap-2 items-start">
                      <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-red-700">{error}</p>
                    </div>
                  )}

                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1.5 uppercase tracking-wider">
                        Personel Kodu
                      </label>
                      <input
                        type="text"
                        placeholder="CK-K42"
                        value={personCode}
                        onChange={(e) => setPersonCode(e.target.value.toUpperCase())}
                        disabled={busy}
                        className="w-full px-4 py-3 bg-slate-50 border-2 border-slate-200 rounded-2xl focus:outline-none focus:border-amber-500 focus:bg-white focus:ring-4 focus:ring-amber-500/10 transition-all duration-200 disabled:opacity-50 font-mono"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1.5 uppercase tracking-wider">
                        TC Kimlik Son 4 Hane
                      </label>
                      <input
                        type="text"
                        inputMode="numeric"
                        placeholder="1234"
                        value={last4Tc}
                        onChange={(e) => {
                          const val = e.target.value.replace(/\D/g, '').slice(0, 4);
                          setLast4Tc(val);
                        }}
                        disabled={busy}
                        maxLength={4}
                        className="w-full px-4 py-3 font-mono text-lg tracking-widest bg-slate-50 border-2 border-slate-200 rounded-2xl focus:outline-none focus:border-amber-500 focus:bg-white focus:ring-4 focus:ring-amber-500/10 transition-all duration-200 disabled:opacity-50"
                        required
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={busy || !personCode || last4Tc.length !== 4}
                    className="w-full py-4 px-4 bg-gradient-to-r from-amber-500 to-orange-600 text-white rounded-2xl font-bold hover:shadow-xl hover:shadow-amber-500/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 hover:-translate-y-0.5"
                  >
                    {busy ? (
                      <span className="inline-flex items-center justify-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin" /> Giriş yapılıyor...
                      </span>
                    ) : (
                      'Giriş Yap'
                    )}
                  </button>
                </form>
              )}
            </div>
          </div>

          <p className="text-[11px] text-blue-100/50 text-center mt-6 flex items-center justify-center gap-1">
            <Sparkles className="w-3 h-3" />
            Bilgilerin güvenli şekilde iletilir
          </p>
        </div>
      </div>

      <style jsx>{`
        @keyframes fade-in-down {
          from {
            opacity: 0;
            transform: translateY(-12px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(12px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes step-in {
          from {
            opacity: 0;
            transform: translateX(8px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          25% { transform: translateX(-6px); }
          75% { transform: translateX(6px); }
        }
        @keyframes float-1 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(40px, -30px) scale(1.05); }
          66% { transform: translate(-20px, 30px) scale(0.95); }
        }
        @keyframes float-2 {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(-50px, 20px) scale(1.1); }
        }
        @keyframes float-3 {
          0%, 100% { transform: translate(0, 0); }
          33% { transform: translate(30px, 40px); }
          66% { transform: translate(-30px, -20px); }
        }
        :global(.animate-fade-in-down) {
          animation: fade-in-down 0.6s ease-out;
        }
        :global(.animate-fade-in-up) {
          animation: fade-in-up 0.7s ease-out 0.1s backwards;
        }
        :global(.animate-step-in) {
          animation: step-in 0.35s ease-out;
        }
        :global(.animate-shake) {
          animation: shake 0.4s ease-in-out;
        }
        :global(.orb) {
          position: absolute;
          border-radius: 50%;
          filter: blur(80px);
          mix-blend-mode: screen;
          will-change: transform;
        }
        :global(.orb-1) {
          width: 400px;
          height: 400px;
          background: radial-gradient(circle, rgba(96, 165, 250, 0.6), transparent 70%);
          top: -100px;
          left: -100px;
          animation: float-1 18s ease-in-out infinite;
        }
        :global(.orb-2) {
          width: 350px;
          height: 350px;
          background: radial-gradient(circle, rgba(232, 217, 181, 0.4), transparent 70%);
          bottom: -80px;
          right: -100px;
          animation: float-2 22s ease-in-out infinite;
        }
        :global(.orb-3) {
          width: 280px;
          height: 280px;
          background: radial-gradient(circle, rgba(139, 92, 246, 0.4), transparent 70%);
          top: 40%;
          right: 20%;
          animation: float-3 25s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
