import { Sidebar } from '@/components/sidebar';
import {
  getInvoiceSummary,
  getSidebarCounts,
  listInvoices,
  type InvoiceSummary,
  type RestaurantInvoice,
  type SidebarCounts,
} from '@/lib/api';

import { FaturalarView } from './view';

export const dynamic = 'force-dynamic';

export default async function FaturalarPage({
  searchParams,
}: {
  searchParams: Promise<{ ay?: string }>;
}) {
  const { ay } = await searchParams;
  const period = ay ?? '2026-03';

  let invoices: RestaurantInvoice[] = [];
  let summary: InvoiceSummary | null = null;
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  try {
    [invoices, summary, counts] = await Promise.all([
      listInvoices(period),
      getInvoiceSummary(period),
      getSidebarCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="faturalar" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <FaturalarView
            invoices={invoices}
            summary={summary}
            period={period}
          />
        )}
      </main>
    </div>
  );
}
