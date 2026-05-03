import { notFound } from 'next/navigation';

import {
  getPersonnel,
  getPersonnelPayroll,
  type PayrollRow,
  type Personnel,
} from '@/lib/api';
import { BordroPrint } from './print';

export const dynamic = 'force-dynamic';

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
  try {
    [payroll, personnel] = await Promise.all([
      getPersonnelPayroll(personId, period),
      getPersonnel(personId).catch(() => null),
    ]);
  } catch {
    notFound();
  }

  if (!payroll) notFound();

  return <BordroPrint payroll={payroll} personnel={personnel} period={period} />;
}
