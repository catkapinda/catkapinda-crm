'use client';

import { useEffect, useRef, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  ArrowLeft, Download, AlertCircle, ShieldCheck,
  PenTool, Check, X, Calendar, ChevronRight, FileText, Loader2,
} from 'lucide-react';
import Link from 'next/link';

import {
  getMyBordroSignature,
  listMyBordroPeriods,
  signMyBordro,
  type BordroSignature,
  type CourierBordroPeriod,
} from '@/lib/courier-api';
import { SignaturePad } from '@/components/signature-pad';

type BordroData = {
  personnel_id: number;
  period: string;
  total_brut: number;
  total_deductions: number;
  total_net: number;
  detail?: {
    [key: string]: unknown;
  };
};

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string): string {
  if (!p) return '';
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return d.toLocaleString('tr-TR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function BordroContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const period = searchParams.get('period') || '';

  // Period yoksa liste sayfasını göster
  if (!period) {
    return <BordroListView />;
  }
  return <BordroDetailView period={period} router={router} />;
}

// ──────────────────────────────────────────────────────────
// Bordro liste — period yoksa burası açılır
// ──────────────────────────────────────────────────────────
function BordroListView() {
  const router = useRouter();
  const [periods, setPeriods] = useState<CourierBordroPeriod[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('courier_token') : null;
    if (!token) {
      router.push('/kurye');
      return;
    }
    listMyBordroPeriods()
      .then(setPeriods)
      .catch((e) => setError(e instanceof Error ? e.message : 'Yüklenemedi'))
      .finally(() => setIsLoading(false));
  }, [router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 pb-20">
      <div className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link
            href="/kurye/dashboard"
            className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900 transition"
          >
            <ArrowLeft className="w-4 h-4" /> Pano
          </Link>
          <h1 className="font-bold text-slate-900">Bordrolarım</h1>
          <div className="w-12" />
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6">
        <div className="mb-5 animate-fade-in">
          <h2 className="text-2xl font-bold text-slate-900">Bordro Geçmişi</h2>
          <p className="text-sm text-slate-500 mt-1">
            Aylık net hakedişlerini incele, PDF olarak indir, dijital olarak imzala
          </p>
        </div>

        {isLoading ? (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-12 text-center">
            <Loader2 className="w-8 h-8 text-blue-600 mx-auto mb-3 animate-spin" />
            <p className="text-sm text-slate-500">Bordrolar yükleniyor...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex gap-3 items-start">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        ) : periods.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-12 text-center">
            <Calendar className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="font-bold text-slate-900 mb-1">Henüz bordron yok</h3>
            <p className="text-sm text-slate-500">
              Puantaj girilmeye başlandığında bordroların burada listelenecek
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {periods.map((p, idx) => (
              <Link
                key={p.period}
                href={`/kurye/bordro?period=${p.period}`}
                className="group block bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300 overflow-hidden animate-stagger"
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <div className="p-5 flex items-center gap-4">
                  <div
                    className={`w-14 h-14 rounded-2xl flex flex-col items-center justify-center flex-shrink-0 shadow-md ${
                      p.is_signed
                        ? 'bg-gradient-to-br from-emerald-500 to-emerald-700 text-white shadow-emerald-500/30'
                        : 'bg-gradient-to-br from-blue-500 to-blue-700 text-white shadow-blue-500/30'
                    }`}
                  >
                    <span className="text-[10px] font-bold uppercase opacity-80">
                      {formatPeriod(p.period).split(' ')[0].slice(0, 3)}
                    </span>
                    <span className="font-display text-lg font-bold leading-none">
                      {p.period.split('-')[0]}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-bold text-slate-900">
                        {formatPeriod(p.period)}
                      </h3>
                      {p.is_signed ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                          <ShieldCheck className="w-3 h-3" /> İmzalı
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-[10px] font-bold uppercase tracking-wider text-amber-700">
                          <PenTool className="w-3 h-3" /> İmza bekliyor
                        </span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-2 mt-1">
                      <span className="font-mono font-bold text-emerald-700 text-lg tabular-nums">
                        {p.total_net.toLocaleString('tr-TR', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                        <span className="text-xs text-emerald-600/70 ml-0.5">₺</span>
                      </span>
                      <span className="text-xs text-slate-400">net</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {p.ana_days} gün çalışma · brüt{' '}
                      {p.total_brut.toLocaleString('tr-TR', { maximumFractionDigits: 0 })} ₺
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-300 group-hover:text-slate-600 group-hover:translate-x-1 transition-all flex-shrink-0" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes stagger {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        :global(.animate-fade-in) {
          animation: fade-in 0.4s ease-out;
        }
        :global(.animate-stagger) {
          animation: stagger 0.5s ease-out backwards;
        }
      `}</style>
    </div>
  );
}

// ──────────────────────────────────────────────────────────
// Bordro detay — period varsa burası
// ──────────────────────────────────────────────────────────
function BordroDetailView({ period, router }: { period: string; router: ReturnType<typeof useRouter> }) {
  const [bordro, setBordro] = useState<BordroData | null>(null);
  const [signature, setSignature] = useState<BordroSignature | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);
  const [showSignModal, setShowSignModal] = useState(false);
  const [signBusy, setSignBusy] = useState(false);
  const [signError, setSignError] = useState<string | null>(null);
  const [hasSigStrokes, setHasSigStrokes] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const padContainerRef = useRef<HTMLDivElement>(null);

  const token =
    typeof window !== 'undefined' ? localStorage.getItem('courier_token') : null;

  useEffect(() => {
    if (!token) {
      router.push('/kurye');
      return;
    }

    const fetchAll = async () => {
      try {
        const [bordroRes, sigRes] = await Promise.all([
          fetch(`/api/courier/my-bordro?period=${period}`, {
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          }),
          getMyBordroSignature(period).catch(() => null),
        ]);

        if (!bordroRes.ok) {
          if (bordroRes.status === 401) {
            localStorage.removeItem('courier_token');
            router.push('/kurye');
            return;
          }
          throw new Error('Bordro yüklenemedi');
        }

        const data: BordroData = await bordroRes.json();
        setBordro(data);
        if (sigRes) setSignature(sigRes);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Sunucu hatası');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAll();
  }, [token, router, period]);

  const handleDownloadPdf = async () => {
    if (!token || !period) return;

    setIsDownloading(true);
    try {
      const res = await fetch(`/api/courier/my-bordro/pdf?period=${period}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        throw new Error('PDF indirilemedi');
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bordro-${period}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'PDF indirme hatası');
    } finally {
      setIsDownloading(false);
    }
  };

  const showToast = (text: string) => {
    setToast(text);
    setTimeout(() => setToast(null), 3500);
  };

  const handleSubmitSignature = async () => {
    setSignError(null);
    if (!acceptedTerms) {
      setSignError('Onay kutusunu işaretlemeden imzalayamazsınız');
      return;
    }
    // Container içindeki canvas'tan data URL al
    const canvas = padContainerRef.current?.querySelector('canvas') as HTMLCanvasElement | null;
    if (!canvas) {
      setSignError('İmza alanı bulunamadı');
      return;
    }
    const handle = (
      canvas as unknown as { __sigHandle?: { toDataUrl: () => string | null; isEmpty: () => boolean } }
    ).__sigHandle;
    if (!handle || handle.isEmpty()) {
      setSignError('Lütfen imzanızı atın');
      return;
    }
    const dataUrl = handle.toDataUrl();
    if (!dataUrl) {
      setSignError('İmza okunamadı');
      return;
    }

    setSignBusy(true);
    try {
      const result = await signMyBordro(period, dataUrl);
      setSignature(result);
      setShowSignModal(false);
      showToast('Bordrunuz başarıyla imzalandı');
    } catch (err) {
      setSignError(err instanceof Error ? err.message : 'İmza kaydedilemedi');
    } finally {
      setSignBusy(false);
    }
  };

  const isSigned = signature?.is_signed === true;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 pb-12">
      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link
            href="/kurye/dashboard"
            className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
          >
            <ArrowLeft className="w-4 h-4" /> Pano
          </Link>
          <h1 className="font-semibold text-slate-900">Bordro</h1>
          <div className="w-12" />
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">
            {formatPeriod(period)}
          </h2>
          <p className="text-sm text-slate-500 mt-1">
            Bu ayki net hakedişiniz aşağıda görüntülenmektedir
          </p>
        </div>

        {isLoading ? (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-12 text-center">
            <div className="animate-spin h-8 w-8 border-4 border-slate-200 border-t-blue-600 rounded-full mx-auto mb-3" />
            <p className="text-slate-500 text-sm">Bordro yükleniyor...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex gap-3 items-start">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        ) : !bordro ? (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-12 text-center">
            <p className="text-slate-500">Bordro verisi bulunamadı</p>
          </div>
        ) : (
          <>
            {/* SUMMARY card */}
            <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
              <div className="grid grid-cols-3 divide-x divide-slate-100">
                <div className="p-4 text-center">
                  <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-1">
                    Toplam Brüt
                  </div>
                  <div className="text-lg font-bold text-slate-900 tabular-nums">
                    {(bordro.total_brut || 0).toLocaleString('tr-TR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                    <span className="text-xs text-slate-500 ml-1">₺</span>
                  </div>
                </div>
                <div className="p-4 text-center">
                  <div className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold mb-1">
                    Kesintiler
                  </div>
                  <div className="text-lg font-bold text-red-600 tabular-nums">
                    −
                    {(bordro.total_deductions || 0).toLocaleString('tr-TR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                    <span className="text-xs text-slate-500 ml-1">₺</span>
                  </div>
                </div>
                <div className="p-4 text-center bg-emerald-50/40">
                  <div className="text-[11px] uppercase tracking-wider text-emerald-700 font-semibold mb-1">
                    Net Ödeme
                  </div>
                  <div className="text-lg font-bold text-emerald-700 tabular-nums">
                    {(bordro.total_net || 0).toLocaleString('tr-TR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                    <span className="text-xs text-emerald-700/70 ml-1">₺</span>
                  </div>
                </div>
              </div>
              <div className="border-t border-slate-100 px-4 py-3 bg-slate-50/50">
                <button
                  onClick={handleDownloadPdf}
                  disabled={isDownloading}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-slate-900 text-white rounded-lg font-semibold hover:bg-slate-800 disabled:opacity-50 transition"
                >
                  <Download className="w-4 h-4" />
                  {isDownloading ? 'İndiriliyor...' : 'Detaylı PDF İndir'}
                </button>
              </div>
            </div>

            {/* SIGNATURE card */}
            {isSigned ? (
              <div className="bg-gradient-to-br from-emerald-50 to-emerald-100/40 border border-emerald-200 rounded-2xl p-5 shadow-sm">
                <div className="flex items-start gap-3">
                  <div className="w-11 h-11 rounded-xl bg-emerald-500 text-white flex items-center justify-center flex-shrink-0 shadow">
                    <ShieldCheck className="w-5 h-5" strokeWidth={2.4} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-emerald-900 text-base">
                      Bu bordro imzalandı
                    </div>
                    <div className="text-xs text-emerald-700 mt-1">
                      İmza tarihi: {formatDateTime(signature?.signed_at)}
                    </div>
                    {signature?.ip_address && (
                      <div className="text-[11px] text-emerald-700/70 font-mono mt-0.5">
                        IP: {signature.ip_address}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 shadow-sm">
                <div className="flex items-start gap-3 mb-4">
                  <div className="w-11 h-11 rounded-xl bg-amber-500 text-white flex items-center justify-center flex-shrink-0 shadow">
                    <PenTool className="w-5 h-5" strokeWidth={2.4} />
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-amber-900 text-base">
                      Bordronuzu Onaylayın
                    </div>
                    <div className="text-xs text-amber-700 mt-1 leading-relaxed">
                      Net ödemenizin doğruluğunu kontrol edip dijital olarak imzalayın.
                      İmzaladıktan sonra muhasebeye yansır.
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setShowSignModal(true);
                    setSignError(null);
                    setAcceptedTerms(false);
                    setHasSigStrokes(false);
                  }}
                  className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-600 text-white rounded-lg font-semibold hover:bg-amber-700 transition shadow"
                >
                  <PenTool className="w-4 h-4" /> Bordroyu İmzala
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Sign modal */}
      {showSignModal && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-0 sm:p-4">
          <div className="bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl w-full max-w-md max-h-[95vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b border-slate-100 px-5 py-4 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900">Bordroyu İmzala</h3>
                <p className="text-xs text-slate-500">{formatPeriod(period)}</p>
              </div>
              <button
                onClick={() => !signBusy && setShowSignModal(false)}
                className="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center text-slate-500"
                disabled={signBusy}
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {/* Net özet */}
              {bordro && (
                <div className="bg-slate-50 rounded-xl p-3 text-center">
                  <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
                    Onaylayacağınız net
                  </div>
                  <div className="text-2xl font-bold text-emerald-700 tabular-nums mt-0.5">
                    {(bordro.total_net || 0).toLocaleString('tr-TR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}{' '}
                    ₺
                  </div>
                </div>
              )}

              {/* Imza alanı */}
              <div ref={padContainerRef}>
                <SignaturePad height={180} onChange={(empty) => setHasSigStrokes(!empty)} />
              </div>

              {/* Onay metni */}
              <label className="flex items-start gap-2 text-xs text-slate-700 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={acceptedTerms}
                  onChange={(e) => {
                    setAcceptedTerms(e.target.checked);
                    setSignError(null);
                  }}
                  className="mt-0.5 w-4 h-4 accent-amber-600"
                />
                <span>
                  {formatPeriod(period)} dönemi için yukarıdaki net ödeme tutarını
                  inceledim ve doğru olduğunu kabul ediyorum.
                </span>
              </label>

              {signError && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-xs p-2 rounded-lg flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{signError}</span>
                </div>
              )}
            </div>

            <div className="sticky bottom-0 bg-white border-t border-slate-100 p-4 flex gap-2">
              <button
                onClick={() => setShowSignModal(false)}
                disabled={signBusy}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold border border-slate-300 text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition"
              >
                İptal
              </button>
              <button
                onClick={handleSubmitSignature}
                disabled={signBusy || !hasSigStrokes || !acceptedTerms}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-40 disabled:cursor-not-allowed transition shadow"
              >
                {signBusy ? 'Kaydediliyor...' : 'İmzala'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
          <div className="px-4 py-3 rounded-xl shadow-lg bg-emerald-600 text-white text-sm font-medium flex items-center gap-2">
            <Check className="w-4 h-4" strokeWidth={2.5} />
            {toast}
          </div>
        </div>
      )}
    </div>
  );
}

export default function BordroPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-screen bg-slate-50">
          <div className="animate-spin h-8 w-8 border-4 border-slate-200 border-t-blue-600 rounded-full" />
        </div>
      }
    >
      <BordroContent />
    </Suspense>
  );
}
