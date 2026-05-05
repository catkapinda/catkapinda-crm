'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertCircle, ArrowLeft, MessageSquare, Phone, Shield } from 'lucide-react';

import { requestLoginOtp, verifyLoginOtp } from '@/lib/courier-api';

type Step = 'phone' | 'otp' | 'fallback';

export default function CourierLoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('phone');

  // Phone step
  const [phone, setPhone] = useState('');

  // OTP step
  const [otp, setOtp] = useState('');
  const [maskedPhone, setMaskedPhone] = useState('');
  const [resendIn, setResendIn] = useState(0);

  // Fallback (eski yöntem) step
  const [personCode, setPersonCode] = useState('');
  const [last4Tc, setLast4Tc] = useState('');

  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const otpInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (step === 'otp' && otpInputRef.current) {
      otpInputRef.current.focus();
    }
  }, [step]);

  // Resend cooldown timer
  useEffect(() => {
    if (resendIn <= 0) return;
    const id = setInterval(() => setResendIn((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [resendIn]);

  const handleRequestOtp = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError('');
    setBusy(true);
    try {
      const result = await requestLoginOtp(phone);
      setMaskedPhone(result.masked_phone);
      setResendIn(result.cooldown_seconds || 60);
      setStep('otp');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kod gönderilemedi');
    } finally {
      setBusy(false);
    }
  };

  const handleVerifyOtp = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setError('');
    if (otp.length !== 6) {
      setError('6 haneli kodu girin');
      return;
    }
    setBusy(true);
    try {
      const result = await verifyLoginOtp(phone, otp);
      localStorage.setItem('courier_token', result.token);
      router.push('/kurye/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kod doğrulanamadı');
      setBusy(false);
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100 flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 text-white shadow-lg mb-3">
            <span className="font-bold text-2xl">Ç</span>
          </div>
          <h1 className="font-bold text-2xl text-slate-900">Çat Kapında</h1>
          <p className="text-sm text-slate-500 mt-0.5">Kurye Portalı</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden">
          {step === 'phone' && (
            <form onSubmit={handleRequestOtp} className="p-6 space-y-4">
              <div className="flex items-start gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                  <Phone className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <h2 className="font-semibold text-slate-900">Telefon Numaranız</h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Kayıtlı numaraya 6 haneli giriş kodu göndereceğiz
                  </p>
                </div>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex gap-2 items-start">
                  <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-red-700">{error}</p>
                </div>
              )}

              <div>
                <input
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="0555 555 55 55"
                  value={phone}
                  onChange={(e) => {
                    setPhone(e.target.value);
                    setError('');
                  }}
                  disabled={busy}
                  className="w-full px-4 py-3 text-lg font-mono border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:opacity-50"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={busy || !phone.trim()}
                className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow"
              >
                {busy ? 'Kod gönderiliyor...' : 'Kod Gönder'}
              </button>

              <button
                type="button"
                onClick={() => setStep('fallback')}
                disabled={busy}
                className="w-full text-xs text-slate-500 hover:text-slate-700 underline pt-2 disabled:opacity-50"
              >
                SMS gelmiyor mu? Personel kodu ile gir
              </button>
            </form>
          )}

          {step === 'otp' && (
            <form onSubmit={handleVerifyOtp} className="p-6 space-y-4">
              <button
                type="button"
                onClick={() => {
                  setStep('phone');
                  setOtp('');
                  setError('');
                }}
                disabled={busy}
                className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 disabled:opacity-50"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Numara değiştir
              </button>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <h2 className="font-semibold text-slate-900">SMS ile gelen kod</h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {maskedPhone} numarasına gönderildi
                  </p>
                </div>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex gap-2 items-start">
                  <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-red-700">{error}</p>
                </div>
              )}

              <div>
                <input
                  ref={otpInputRef}
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  pattern="\d{6}"
                  placeholder="● ● ● ● ● ●"
                  value={otp}
                  onChange={(e) => {
                    const val = e.target.value.replace(/\D/g, '').slice(0, 6);
                    setOtp(val);
                    setError('');
                  }}
                  disabled={busy}
                  className="w-full px-4 py-4 text-3xl font-mono font-bold tracking-[0.5em] text-center border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:opacity-50"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={busy || otp.length !== 6}
                className="w-full py-3 px-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow"
              >
                {busy ? 'Doğrulanıyor...' : 'Giriş Yap'}
              </button>

              <div className="text-center">
                {resendIn > 0 ? (
                  <p className="text-xs text-slate-500">
                    Yeniden gönderim için <strong>{resendIn}s</strong> bekleyin
                  </p>
                ) : (
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={busy}
                    className="text-xs text-blue-600 hover:text-blue-700 font-semibold underline disabled:opacity-50"
                  >
                    Kodu yeniden gönder
                  </button>
                )}
              </div>
            </form>
          )}

          {step === 'fallback' && (
            <form onSubmit={handleFallbackLogin} className="p-6 space-y-4">
              <button
                type="button"
                onClick={() => {
                  setStep('phone');
                  setError('');
                }}
                disabled={busy}
                className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 disabled:opacity-50"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> SMS ile gir
              </button>

              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0">
                  <Shield className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <h2 className="font-semibold text-slate-900">Personel Kodu ile Giriş</h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    SMS alamıyorsanız bu yöntemi kullanın
                  </p>
                </div>
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex gap-2 items-start">
                  <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-red-700">{error}</p>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
                  Personel Kodu
                </label>
                <input
                  type="text"
                  placeholder="CK-K42"
                  value={personCode}
                  onChange={(e) => setPersonCode(e.target.value.toUpperCase())}
                  disabled={busy}
                  className="w-full px-3 py-2.5 border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:opacity-50"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
                  TC Kimlik No&apos;nun Son 4 Hanesi
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
                  className="w-full px-3 py-2.5 font-mono text-lg tracking-widest border border-slate-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:opacity-50"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={busy || !personCode || last4Tc.length !== 4}
                className="w-full py-3 px-4 bg-amber-600 text-white rounded-lg font-semibold hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition shadow"
              >
                {busy ? 'Giriş yapılıyor...' : 'Giriş Yap'}
              </button>
            </form>
          )}
        </div>

        <p className="text-[11px] text-slate-500 text-center mt-4">
          Bilgileriniz güvenli şekilde iletilir ve saklanır.
        </p>
      </div>
    </div>
  );
}
