import { Metadata } from 'next';
import { getSidebarCounts, listProfileChanges } from '@/lib/api';
import { ProfilOnayView } from './view';

export const metadata: Metadata = {
  title: 'Profil Onayları | CRM',
  description: 'Kurye profil değişikliklerini onayla veya reddet',
};

export default async function ProfilOnayPage() {
  const [changes, counts] = await Promise.all([
    listProfileChanges(),
    getSidebarCounts(),
  ]);

  return (
    <ProfilOnayView
      initialChanges={changes}
      initialCounts={counts}
    />
  );
}
