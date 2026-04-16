from app.schemas.announcements import (
    AnnouncementsDashboardResponse,
    AnnouncementsModuleStatus,
    AnnouncementHeroMetric,
    AnnouncementSnapshot,
    AnnouncementSnapshotItem,
)


def build_announcements_status() -> AnnouncementsModuleStatus:
    return AnnouncementsModuleStatus(
        module="announcements",
        status="active",
        next_slice="release-notes-board",
    )


def build_announcements_dashboard() -> AnnouncementsDashboardResponse:
    return AnnouncementsDashboardResponse(
        module="announcements",
        status="active",
        kicker="Güncellemeler ve Duyurular",
        title="Sistemdeki son iyileştirmeler ve takip notları",
        description=(
            "Operasyon ekibinin son yayınlanan geliştirmeleri tek ekranda görmesi için "
            "hazırlanan hızlı özet alanı."
        ),
        metrics=[
            AnnouncementHeroMetric(label="Giriş Deneyimi", value="Yenilendi"),
            AnnouncementHeroMetric(label="Personel Formları", value="Güncellendi"),
            AnnouncementHeroMetric(label="Restoran Fiyatlama", value="Dinamik"),
            AnnouncementHeroMetric(label="Motor Kira Hesabı", value="Gün Bazlı"),
        ],
        snapshots=[
            AnnouncementSnapshot(
                title="Operasyon ve Form Akışları",
                items=[
                    AnnouncementSnapshotItem(
                        label="Personel Yönetimi",
                        value="Ekleme sonrası görünür başarı mesajı ve son eklenen kartı",
                    ),
                    AnnouncementSnapshotItem(
                        label="Zorunlu Alanlar",
                        value="Kırmızı yıldız ile işaretlenir ve boş geçilemez",
                    ),
                    AnnouncementSnapshotItem(
                        label="Rol / Maliyet Modeli",
                        value="Personel formunda otomatik eşlenir",
                    ),
                    AnnouncementSnapshotItem(
                        label="Restoran Fiyat Modelleri",
                        value="Seçime göre sadece ilgili alanlar görünür",
                    ),
                ],
            ),
            AnnouncementSnapshot(
                title="Finans ve Hesaplama",
                items=[
                    AnnouncementSnapshotItem(
                        label="Motor Kira",
                        value="13.000 / 30 x çalışılan gün formülüyle hesaplanır",
                    ),
                    AnnouncementSnapshotItem(
                        label="Kesinti Senkronu",
                        value="Puantaj ekleme, güncelleme ve silmede otomatik yenilenir",
                    ),
                    AnnouncementSnapshotItem(
                        label="Hakediş / Raporlar",
                        value="Açılırken sistem kesintileri yeniden senkronlanır",
                    ),
                    AnnouncementSnapshotItem(
                        label="Şifre Sıfırlama",
                        value="E-posta ve SMS ile kurtarma akışı desteklenir",
                    ),
                ],
            ),
        ],
        notes_title="Notlar",
        notes_body=(
            "Canlı ortamda bir değişiklik görünmüyorsa yayın tarafında bazen elle yeniden dağıtım "
            "çalıştırmak gerekebilir. Yayın tamamlandıktan sonra sayfayı sert yenilemek en güvenli kontroldür."
        ),
        footer_note=(
            "Bu alan sabit duyuru panosu gibi çalışır; yeni operasyon notları gerektiğinde "
            "kolayca genişletilebilir."
        ),
    )
