'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import {
  AlertCircle, ArrowRight, CheckCircle2, Eye, EyeOff,
  Loader2, Lock, ShieldCheck,
} from 'lucide-react';

import { resetPasswordWithToken } from '@/lib/api';

export function SifreSifirlaView({ token }: { token: string }) {
  const router = useRouter();
  const [pwd, setPwd] = useState('');
  const [pwd2, setPwd2] = useState('');
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) {
      setError('Sıfırlama linki geçersiz veya eksik.');
      return;
    }
    if (pwd.length < 6) {
      setError('Parola en az 6 karakter olmalı.');
      return;
    }
    if (pwd !== pwd2) {
      setError('Parolalar eşleşmiyor.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await resetPasswordWithToken(token, pwd);
      setDone(true);
      setTimeout(() => router.push('/login'), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Parola değiştirilemedi');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-cream-50 to-blue-50/40 p-6">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-2xl border border-border p-8">
        <div className="flex items-center gap-3 mb-6">
          <Image
            src="/catkapinda-logo.png"
            alt="Çat Kapında"
            width={40}
            height={40}
            className="object-contain"
          />
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-text-3 font-bold">
              CRM
            </div>
            <div className="font-display text-xl font-bold tracking-tight text-text">
              Çat Kapında
            </div>
          </div>
        </div>

        <h1 className="font-display text-2xl font-bold tracking-tight text-text mb-1">
          Yeni Parola Belirle
        </h1>
        <p className="text-text-3 text-[13px] mb-6">
          En az 6 karakter olmalı. Mümkünse harf + rakam karışımı kullanın.
        </p>

        {done ? (
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-7 h-7 text-emerald-600 flex-shrink-0" />
              <div>
                <div className="font-semibold text-emerald-800 mb-1">
                  Parola güncellendi
                </div>
                <p className="text-[13px] text-emerald-700">
                  Girişe yönlendiriliyorsunuz...
                </p>
              </div>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[11.5px] font-bold text-text-2 uppercase tracking-wider mb-1.5">
                Yeni Parola
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-3" strokeWidth={2.2} />
                <input
                  type={show ? 'text' : 'password'}
                  value={pwd}
                  onChange={(e) => setPwd(e.target.value)}
                  placeholder="••••••••"
                  autoFocus
                  required
                  className="w-full pl-10 pr-10 py-3 rounded-xl border border-border text-sm focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
                />
                <button
                  type="button"
                  onClick={() => setShow((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-3 hover:text-text-2"
                >
                  {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-[11.5px] font-bold text-text-2 uppercase tracking-wider mb-1.5">
                Parola (Tekrar)
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-3" strokeWidth={2.2} />
                <input
                  type={show ? 'text' : 'password'}
                  value={pwd2}
                  onChange={(e) => setPwd2(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full pl-10 pr-3 py-3 rounded-xl border border-border text-sm focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/20 transition bg-white"
                />
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
              className="w-full py-3 rounded-xl bg-gradient-to-r from-brand-dark to-brand text-white font-bold text-sm shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all disabled:opacity-60 inline-flex items-center justify-center gap-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>Parolayı Güncelle <ArrowRight className="w-4 h-4" strokeWidth={2.4} /></>
              )}
            </button>

            <Link
              href="/login"
              className="block text-center text-[12px] text-text-3 hover:text-brand transition font-semibold"
            >
              ← Girişe dön
            </Link>
          </form>
        )}

        <div className="mt-6 pt-4 border-t border-border/60 text-[11px] text-text-3 flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5" />
          Çat Kapında CRM — Güvenli oturum
        </div>
      </div>
    </div>
  );
}
