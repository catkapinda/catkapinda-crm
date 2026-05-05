import { Metadata } from 'next';
import { ProfilimView } from './view';

export const metadata: Metadata = {
  title: 'Profilim | Kurye Portalı',
  description: 'Kişisel bilgilerinizi düzenleyin ve talepleri takip edin',
};

export default function ProfilimPage() {
  return <ProfilimView />;
}
