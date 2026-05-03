import { Sidebar } from '@/components/sidebar';
import {
  getEquipmentCatalog,
  getSidebarCounts,
  listEquipmentAssignments,
  listPersonnel,
  type EquipmentAssignment,
  type EquipmentCatalogItem,
  type Personnel,
  type SidebarCounts,
} from '@/lib/api';
import { EkipmanView } from './view';

export const dynamic = 'force-dynamic';

export default async function EkipmanZimmetPage() {
  let assignments: EquipmentAssignment[] = [];
  let catalog: EquipmentCatalogItem[] = [];
  let personnel: Personnel[] = [];
  let counts: SidebarCounts | null = null;
  let error: string | null = null;

  try {
    [assignments, catalog, personnel, counts] = await Promise.all([
      listEquipmentAssignments(),
      getEquipmentCatalog().catch(() => []),
      listPersonnel('Aktif').catch(() => []),
      getSidebarCounts().catch(() => null),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'API hatası';
  }

  return (
    <div className="grid grid-cols-[252px_1fr] min-h-screen">
      <Sidebar active="ekipman" counts={counts} />
      <main className="p-8 max-w-[1500px]">
        {error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-5 text-red-700 text-sm">
            <strong>API hatası:</strong> {error}
          </div>
        ) : (
          <EkipmanView
            assignments={assignments}
            catalog={catalog}
            personnel={personnel}
          />
        )}
      </main>
    </div>
  );
}
