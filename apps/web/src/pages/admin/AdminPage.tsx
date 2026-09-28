import { Placeholder } from '../../components/Placeholder';

/**
 * Admin kabuk sayfaları: menü başlığı + "faz 1'de geliyor" kartı.
 */
export function AdminPage({ title }: { title: string }) {
  return <Placeholder title={title} note="Bu modül faz 1 tamamlanınca buraya bağlanacak." />;
}
