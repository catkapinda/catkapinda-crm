import { Sidebar } from '@/components/sidebar';
import {
  getCourierRequestCounts,
  getSidebarCounts,
  listCourierRequests,
  listPersonnel,
  type CourierRequest,
  type CourierRequestCounts,
  type Personnel,
  type SidebarCounts,
} from '@/lib/api';

import { TaleplerView } from './view';

export const dynamic = 'force-dynamic';

export default async function TaleplerPage() {
  let requests: CourierRequest[] = [];
  let personnel: Personnel[] = [];
  let counts: SidebarCounts | null = null;
  let reqCounts: CourierRequestCounts | null = null;
  let error: string | null = null;

  try {
    [requests, personnel, counts, reqCounts] = await Promise.all([
      listCourierRequests().catch(() => []),
      listPersonnel('Aktif').catch(() => []),
      getSidebarCounts().catch(() => null),
      getCourierRequestCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="talepler" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <TaleplerView
            requests={requests}
            personnel={personnel}
            initialCounts={reqCounts}
          />
        )}
      </main>
    </div>
  );
}
