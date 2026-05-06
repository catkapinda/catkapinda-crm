import { notFound } from 'next/navigation';

import {
  apiGet,
  getPersonnel,
  getPersonnelPayroll,
  type PayrollRow,
  type Personnel,
} from '@/lib/api';
import { BordroPrint } from './print';

export const dynamic = 'force-dynamic';

// Backend `/api/payroll/signatures/{id}?period=...&include_data=1`
// kayıt yoksa `null`/`{}` döner; varsa şu alanlar gelir:
//   { id, personnel_id, period, signed_at, ip_address, signature_data }
export type BordroSignaturePreview = {
  id?: number;
  personnel_id?: number;
  period?: string;
  signed_at?: string | null;
  ip_address?: string | null;
  signature_data?: string;
};

export default async function BordroPdfPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ ay?: string }>;
}) {
  const { id } = await params;
  const { ay } = await searchParams;
  const personId = parseInt(id, 10);
  if (Number.isNaN(personId)) notFound();
  const period = ay || '2026-03';

  let payroll: PayrollRow | null = null;
  let personnel: Personnel | null = null;
  let signature: BordroSignaturePreview | null = null;
  try {
    [payroll, personnel, signature] = await Promise.all([
      getPersonnelPayroll(personId, period),
      getPersonnel(personId).catch(() => null),
      apiGet<BordroSignaturePreview | null>(
        `/api/payroll/signatures/${personId}?period=${encodeURIComponent(period)}&include_data=true`,
      ).catch(() => null),
    ]);
  } catch {
    notFound();
  }

  if (!payroll) notFound();

  return (
    <BordroPrint
      payroll={payroll}
      personnel={personnel}
      period={period}
      signature={signature && signature.signature_data ? signature : null}
    />
  );
}
