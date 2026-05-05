'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertCircle } from 'lucide-react';

export default function CourierLoginPage() {
  const router = useRouter();
  const [personCode, setPersonCode] = useState('');
  const [last4Tc, setLast4Tc] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/courier/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          person_code: personCode.toUpperCase(),
          last4_tc: last4Tc,
        }),
        credentials: 'include',
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || 'Giriş başarısız');
        setIsLoading(false);
        return;
      }

      const data = await res.json();
      // Tarayıcı cookie'yi otomatik set eder; token'ı da localStorage'a kaydedebiliriz
      localStorage.setItem('courier_token', data.token);

      // Dashboard'a yönlendir
      router.push('/kurye/dashboard');
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Sunucu hatası'
      );
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen px-4 py-8">
      <div className="w-full max-w-sm">
        {/* Card */}
        <div className="bg-white rounded-lg border border-cream-200 shadow-sm p-8">
          <h1 className="text-2xl font-semibold text-text mb-2">Giriş Yap</h1>
          <p className="text-sm text-text-secondary mb-6">
            Bordronuzu görmek ve talep oluşturmak için giriş yapın
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded flex gap-2 items-start">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Person Code */}
            <div>
              <label htmlFor="person_code" className="block text-sm font-medium text-text mb-1">
                Personel Kodu
              </label>
              <input
                id="person_code"
                type="text"
                placeholder="CK-K42"
                value={personCode}
                onChange={(e) => setPersonCode(e.target.value.toUpperCase())}
                disabled={isLoading}
                className="w-full px-3 py-2 border border-cream-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent disabled:opacity-50"
                required
              />
            </div>

            {/* Last 4 TC */}
            <div>
              <label htmlFor="last4_tc" className="block text-sm font-medium text-text mb-1">
                TC Kimlik No'nun Son 4 Hanesi
              </label>
              <input
                id="last4_tc"
                type="text"
                inputMode="numeric"
                placeholder="1234"
                value={last4Tc}
                onChange={(e) => {
                  const val = e.target.value.replace(/\D/g, '').slice(0, 4);
                  setLast4Tc(val);
                }}
                disabled={isLoading}
                maxLength={4}
                className="w-full px-3 py-2 border border-cream-300 rounded-md focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent disabled:opacity-50"
                required
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !personCode || last4Tc.length !== 4}
              className="w-full py-2 px-4 bg-brand text-white rounded-md font-medium hover:bg-brand-dark disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {isLoading ? 'Giriş yapılıyor...' : 'Giriş Yap'}
            </button>
          </form>

          <p className="text-xs text-text-secondary text-center mt-6">
            Bilgileriniz güvenli şekilde iletilir ve saklanır.
          </p>
        </div>
      </div>
    </div>
  );
}
