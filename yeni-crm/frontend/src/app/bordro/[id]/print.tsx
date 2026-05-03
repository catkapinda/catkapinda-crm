'use client';

import { useEffect } from 'react';

import type { PayrollRow, Personnel } from '@/lib/api';

const TR_MONTHS = [
  'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
  'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
];

function formatPeriod(p: string): string {
  const [y, m] = p.split('-').map((s) => parseInt(s, 10));
  if (!y || !m) return p;
  return `${TR_MONTHS[m - 1]} ${y}`;
}

function tr(value: number | null | undefined, digits = 0): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

// Para tutarı: 2 ondalık zorunlu (asla yuvarlama)
function m(value: number | null | undefined): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function BordroPrint({
  payroll, personnel, period,
}: {
  payroll: PayrollRow;
  personnel: Personnel | null;
  period: string;
}) {
  // Sayfa açılınca kısa bir gecikme sonrası yazdır diyaloğunu aç
  useEffect(() => {
    const t = setTimeout(() => {
      // Otomatik açma yerine üstteki butonu bırak
    }, 500);
    return () => clearTimeout(t);
  }, []);

  const total_kesinti = payroll.kesinti_total + payroll.sabit_total + payroll.tevkifat;

  return (
    <div className="bordro-page bg-cream-50 min-h-screen py-8 px-4 print:p-0 print:bg-white">
      {/* Print kontrol — yazdırırken gizli */}
      <div className="max-w-[800px] mx-auto mb-3 flex justify-end gap-2 print:hidden">
        <button
          onClick={() => window.history.back()}
          className="px-3 py-1.5 rounded-lg border border-border bg-bg-surface text-[12.5px] font-medium hover:bg-bg-surface2 transition"
        >
          ← Geri
        </button>
        <button
          onClick={() => window.print()}
          className="px-4 py-1.5 rounded-lg bg-brand text-white text-[12.5px] font-semibold shadow-sm hover:bg-brand-dark transition"
        >
          🖨️ PDF olarak yazdır
        </button>
      </div>

      <div className="bordro-sheet max-w-[800px] mx-auto bg-white shadow-md print:shadow-none border border-border print:border-0">
        {/* Header */}
        <div className="bg-gradient-to-r from-brand-dark to-brand text-white px-8 py-6 print:bg-brand">
          <div className="flex justify-between items-start">
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] opacity-80 font-semibold">
                Çat Kapında · Kurye Bordrosu
              </div>
              <div className="font-display text-2xl font-semibold tracking-tight mt-1">
                {formatPeriod(period)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-wider opacity-80 font-semibold">
                Belge No
              </div>
              <div className="font-mono text-[12.5px] mt-0.5">
                BR-{period.replace('-', '')}-{String(payroll.id).padStart(4, '0')}
              </div>
            </div>
          </div>
        </div>

        {/* Kurye bilgisi */}
        <div className="px-8 py-5 border-b border-border grid grid-cols-2 gap-5 text-[12.5px]">
          <div>
            <Label>Adı Soyadı</Label>
            <Value>{payroll.full_name}</Value>
            <Label className="mt-3">Personel Kodu</Label>
            <Value className="font-mono">{payroll.person_code}</Value>
            <Label className="mt-3">Görev</Label>
            <Value>{payroll.role}</Value>
          </div>
          <div>
            <Label>Restoran</Label>
            <Value>
              {payroll.rest_brand}
              {payroll.rest_branch && ` · ${payroll.rest_branch}`}
            </Value>
            {personnel?.tc_no && (
              <>
                <Label className="mt-3">TC Kimlik No</Label>
                <Value className="font-mono">{personnel.tc_no}</Value>
              </>
            )}
            {personnel?.iban && (
              <>
                <Label className="mt-3">IBAN</Label>
                <Value className="font-mono text-[11.5px]">{personnel.iban}</Value>
              </>
            )}
            {personnel?.tax_office && personnel?.tax_number && (
              <>
                <Label className="mt-3">Vergi Dairesi / No</Label>
                <Value className="font-mono">
                  {personnel.tax_office} · {personnel.tax_number}
                </Value>
              </>
            )}
          </div>
        </div>

        {/* Çalışma özeti */}
        <div className="px-8 py-5 border-b border-border">
          <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-3">
            Aylık Çalışma Özeti
          </div>
          <div className="grid grid-cols-4 gap-3 text-center">
            <Stat label="Çalışılan Gün" value={payroll.ana_days.toString()} />
            <Stat label="Saat" value={tr(Math.round(payroll.ana_hours))} />
            <Stat label="Paket" value={tr(payroll.ana_packages)} />
            <Stat
              label="Destek Günü"
              value={
                payroll.destek_days > 0 ? `+${payroll.destek_days}` : '—'
              }
              color={payroll.destek_days > 0 ? 'text-orange-700' : 'text-text-3'}
            />
          </div>
        </div>

        {/* Brüt detay */}
        <div className="px-8 py-5 border-b border-border">
          <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-3">
            Brüt Hakediş
          </div>
          <div className="space-y-1.5 text-[12.5px]">
            {/* Ana atama satırı: sadece ekstra/destek/kaptan bonusu varsa
                ayrı görünür (yoksa zaten Toplam Brüt = Ana). */}
            {(payroll.destek_brut > 0 ||
              payroll.kaptan_bonus > 0 ||
              payroll.ekstra_mesai_brut > 0) && (
              <Line
                label={payroll.is_fixed_salary ? 'Sabit aylık tutar' : 'Ana atama'}
                value={`${m(payroll.ana_brut)} ₺`}
              />
            )}
            {payroll.ekstra_mesai_brut > 0 && (
              <Line
                label={`Bayram / ekstra mesai (${payroll.ekstra_mesai_days} gün)`}
                value={`+${m(payroll.ekstra_mesai_brut)} ₺`}
                color="text-purple-700"
              />
            )}
            {payroll.destek_brut > 0 && (
              <Line
                label={`Destek vardiyaları (${payroll.destek_days} gün)`}
                value={`+${m(payroll.destek_brut)} ₺`}
                color="text-orange-700"
              />
            )}
            {payroll.kaptan_bonus > 0 && (
              <Line
                label="Kaptan bonusu"
                value={`+${m(payroll.kaptan_bonus)} ₺`}
                color="text-green-700"
              />
            )}
            <div className="flex justify-between font-semibold">
              <span>Toplam Brüt</span>
              <span className="num font-mono text-[14px]">
                {m(payroll.toplam_brut)} ₺
              </span>
            </div>
            {payroll.tevkifat_breakdown.fatura_total !== undefined &&
              payroll.tevkifat_breakdown.fatura_total > 0 && (
                <>
                  <div className="flex justify-between text-[11.5px] mt-1">
                    <span className="font-semibold">
                      Fatura Tutarı (KDV %20 dahil)
                    </span>
                    <span className="num font-mono font-semibold">
                      {m(payroll.tevkifat_breakdown.fatura_total)} ₺
                    </span>
                  </div>
                  <div className="text-[10.5px] text-text-2 font-semibold mt-0.5">
                    ↳ KDV hariç matrah: {m(payroll.tevkifat_breakdown.invoice_base_amount)} ₺ · KDV (%20): {m(payroll.tevkifat_breakdown.vat_amount)} ₺
                  </div>
                </>
              )}
          </div>
        </div>

        {/* Tüm Kesintiler (sabit + manuel + tevkifat) */}
        {(payroll.sabit_total > 0 ||
          payroll.kesinti_groups.length > 0 ||
          payroll.tevkifat > 0) && (
          <div className="px-8 py-5 border-b border-border">
            <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-3">
              Kesintiler & Zimmet
            </div>
            <div className="space-y-1.5 text-[12.5px]">
              {payroll.motor_taksit > 0 && (
                <Line
                  label="Motor satış taksiti"
                  value={`−${m(payroll.motor_taksit)} ₺`}
                  color="text-red-700"
                />
              )}
              {payroll.motor_kira > 0 && (
                <Line
                  label={`Motor kirası${payroll.ana_days < 28 ? ` (${payroll.ana_days} gün × aylık/30)` : ''}`}
                  value={`−${m(payroll.motor_kira)} ₺`}
                  color="text-red-700"
                />
              )}
              {payroll.muhasebe > 0 && (
                <Line
                  label="ÇK Muhasebe bedeli"
                  value={`−${m(payroll.muhasebe)} ₺`}
                  color="text-red-700"
                />
              )}
              {payroll.sirket_acilis > 0 && (
                <Line
                  label="Şirket açılış bedeli (1×)"
                  value={`−${m(payroll.sirket_acilis)} ₺`}
                  color="text-red-700"
                />
              )}
              {payroll.kesinti_groups.map((g) => (
                <div key={g.type}>
                  <Line
                    label={`${g.type} (${g.count} kayıt)`}
                    value={`−${m(g.total)} ₺`}
                    color="text-red-700"
                  />
                  {/* Zimmet detay açıklamaları */}
                  {g.lines.some((l) => l.equipment) && (
                    <div className="ml-4 mt-1 text-[11px] text-text-3 space-y-0.5">
                      {g.lines.map((l, i) => (
                        l.equipment ? (
                          <div key={i} className="flex justify-between">
                            <span>↳ {l.equipment} {l.notes && `· ${l.notes}`}</span>
                            <span className="font-mono">{m(l.amount)} ₺</span>
                          </div>
                        ) : null
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {payroll.tevkifat > 0 && (
                <div className="flex justify-between">
                  <div>
                    <div>KDV Tevkifatı (2/10)</div>
                    <div className="text-[10px] text-text-3 italic">
                      Zorunlu devlet kesintisidir · KDV'nin %20'si
                      ({m(payroll.tevkifat_breakdown.vat_amount)} ₺)
                    </div>
                  </div>
                  <span className="num font-mono font-semibold text-red-700">
                    −{m(payroll.tevkifat)} ₺
                  </span>
                </div>
              )}
              <div className="border-t border-border pt-2 flex justify-between font-semibold">
                <span>Toplam Kesinti</span>
                <span className="num font-mono text-red-700 text-[14px]">
                  −{m(payroll.sabit_total + payroll.kesinti_total + payroll.tevkifat)} ₺
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Net — büyük */}
        <div className="px-8 py-6 bg-gradient-to-br from-brand-dark to-brand text-white">
          <div className="flex justify-between items-end">
            <div>
              <div className="text-[10.5px] uppercase tracking-[0.18em] opacity-80 font-semibold">
                Net Aylık Hakediş
              </div>
              <div className="text-[11px] opacity-85 mt-1">
                Brüt {m(payroll.toplam_brut)} ₺ − Kesinti{' '}
                {m(total_kesinti)} ₺
              </div>
            </div>
            <div className="font-display text-[34px] font-bold tracking-tight num">
              {m(payroll.net)} ₺
            </div>
          </div>
        </div>

        {/* İmza alanları */}
        <div className="px-8 py-6 grid grid-cols-2 gap-12 border-t border-border">
          <div>
            <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-12">
              Düzenleyen
            </div>
            <div className="border-b border-text/30 pb-1.5 text-[11.5px] text-text-2">
              Çat Kapında Teknoloji Lojistik ve Dış Ticaret A.Ş.
            </div>
            <div className="text-[10px] text-text-3 mt-1">
              Tarih: {new Date().toLocaleDateString('tr-TR')}
            </div>
          </div>
          <div>
            <div className="text-[10.5px] uppercase tracking-wider text-text-3 font-bold mb-12">
              Kurye İmza
            </div>
            <div className="border-b border-text/30 pb-1.5 text-[11.5px] text-text-2">
              {payroll.full_name ?? '—'}
            </div>
            <div className="text-[10px] text-text-3 mt-1">
              Tarih: ____________________
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-8 py-4 text-[10.5px] text-text-3 leading-relaxed border-t border-border bg-cream-50/50">
          <div>
            Bu belge <strong>{formatPeriod(period)}</strong> ayına ait kurye
            hakediş bordrosudur. Tutarlar puantaj kayıtları, restoran tarifeleri,
            kesintiler ve zimmet taksitleri üzerinden hesaplanmıştır.
          </div>
          <div className="mt-2 flex justify-between text-[10px]">
            <span className="font-semibold">Çat Kapında CRM Sistemi</span>
            <span className="font-mono">
              Belge: BR-{period.replace('-', '')}-
              {String(payroll.id).padStart(4, '0')}
            </span>
          </div>
        </div>
      </div>

      <style jsx global>{`
        @media print {
          @page {
            size: A4;
            margin: 12mm;
          }
          body { background: white !important; }
          .bordro-page { padding: 0 !important; }
          .bordro-sheet { box-shadow: none !important; border: none !important; }
        }
      `}</style>
    </div>
  );
}

function Label({
  children, className,
}: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`text-[10px] uppercase tracking-wider text-text-3 font-bold ${className ?? ''}`}
    >
      {children}
    </div>
  );
}

function Value({
  children, className,
}: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`text-[13px] text-text font-semibold mt-0.5 ${className ?? ''}`}>
      {children}
    </div>
  );
}

function Stat({
  label, value, color,
}: { label: string; value: string; color?: string }) {
  return (
    <div className="border border-border rounded-lg px-3 py-2.5">
      <div className="text-[9.5px] uppercase tracking-wider text-text-3 font-bold">
        {label}
      </div>
      <div
        className={`font-display text-[20px] font-bold tracking-tight num mt-1 ${color ?? 'text-text'}`}
      >
        {value}
      </div>
    </div>
  );
}

function Line({
  label, value, color,
}: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-text-2">{label}</span>
      <span className={`num font-mono font-semibold ${color ?? 'text-text'}`}>
        {value}
      </span>
    </div>
  );
}
