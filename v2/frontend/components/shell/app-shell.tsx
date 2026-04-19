"use client";

import Link from "next/link";
import { useEffect, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "../auth/auth-provider";
import type { SidebarItem } from "../../lib/navigation";
import { filterSidebarItems, resolveDefaultPath, sidebarItems } from "../../lib/navigation";
import { isPreviewPathname } from "../../lib/preview";

type PreviewMeta = {
  kicker: string;
  title: string;
  description: string;
  relatedLabels: string[];
  reviewPoints: string[];
  signal: string;
  flowNote: string;
};

const navAccentByLabel: Record<string, string> = {
  "Genel Bakış": "#48c6b5",
  Puantaj: "#f4a340",
  Personel: "#7ab8ff",
  Kesintiler: "#ff7d73",
  Ekipman: "#b8d66b",
  "Aylık Hakediş": "#f1d36f",
  "Satın Alma": "#a78bfa",
  Satış: "#60d394",
  Restoranlar: "#ffb86b",
  Raporlar: "#86a7ff",
  Duyurular: "#f6c667",
  "Sistem Kayıtları": "#c0c7d1",
  Profil: "#d7c8ff",
};

const previewMetaByLabel: Record<string, PreviewMeta> = {
  "Genel Bakış": {
    kicker: "Operasyon Merkezi",
    title: "Genel durumu tek merkezden takip et",
    description:
      "Saha, finans, ekipman ve restoran özetlerini aynı ekranda toplayarak hangi modüle önce bakılması gerektiğini gösterir.",
    relatedLabels: ["Puantaj", "Satış", "Ekipman"],
    reviewPoints: [
      "Saha, ticari ve kontrol özetleri hızlı okunuyor mu bak.",
      "Son hareketlerde işlem sahibi, modül ve tarih net görünüyor mu kontrol et.",
      "Kullanıcı hangi modüle geçeceğini kolay anlayabiliyor mu incele.",
    ],
    signal: "Bu ekran, günlük operasyon kontrolü için başlangıç noktası olarak çalışır.",
    flowNote: "Saha kontrolleri için Puantaj, finans ve maliyet kontrolleri için Satış veya Ekipman modülüne geçilebilir.",
  },
  Duyurular: {
    kicker: "Yayın Panosu",
    title: "Son iyileştirmeler ve saha notları burada toplanıyor",
    description:
      "Canlıya çıkan güncellemeleri, operasyon notlarını ve ekibin bilmesi gereken kısa değişiklik özetlerini tek bakışta okumak için hazır.",
    relatedLabels: ["Genel Bakış", "Puantaj", "Raporlar"],
    reviewPoints: [
      "Yayın notlarının hızlı taranıp taranamadığına bak.",
      "Operasyon ekibinin burada gerçekten gündem okuyup okuyamayacağını kontrol et.",
      "Sabit panonun ürün dilinden kopmadan durup durmadığını incele.",
    ],
    signal: "Bu modül, canlı güncellemeleri ve ekip duyurularını tek yerde toplar.",
    flowNote: "Duyurular sonrası Genel Bakış veya Puantaj ekranına geçmek, okunan notların akışa nasıl yansıdığını görmek için iyi bir devam olur.",
  },
  "Puantaj": {
    kicker: "Saha Omurgası",
    title: "Günlük puantaj akışı yeni katta",
    description:
      "Vardiya, destek geçişi ve aylık kayıt temizliği gibi operasyonun en sık dokunulan işlerini hızlı gözlemlemek için hazır.",
    relatedLabels: ["Personel", "Kesintiler", "Restoranlar"],
    reviewPoints: [
      "Günlük giriş akışı yoğun kullanımda hızlı tamamlanıyor mu bak.",
      "Liste, filtre ve tehlikeli aksiyonların ayırt edilebilirliğine odaklan.",
      "Saha operasyonu için hız, netlik ve kontrol dengesi kuruldu mu kontrol et.",
    ],
    signal: "En sık kullanılan modül olduğu için hızlı kayıt ve net kontrol önceliklidir.",
    flowNote: "Puantajdan sonra personel kartı veya kesinti kaydı kontrolü için ilgili modüle geçilebilir.",
  },
  Personel: {
    kicker: "Kadro Yönetimi",
    title: "Kadro kartları ve saha dağılımı burada toparlanıyor",
    description:
      "Personel kartı açma, durum değiştirme, rol ve restoran atamalarını tek yerden yönetmek için kullanılır.",
    relatedLabels: ["Puantaj", "Kesintiler", "Ekipman"],
    reviewPoints: [
      "Kart yoğunluğu yüksek olsa bile sayfa nefes alıyor mu incele.",
      "Aktif-pasif, restoran dağılımı ve iletişim bilgileri kolay taranıyor mu bak.",
      "Yönetici, kayıt durumunu ve eksik alanları hızlı anlayabiliyor mu kontrol et.",
    ],
    signal: "Personel ekranı, kadro kaydı ve saha atamalarını güncel tutmak için ana çalışma alanıdır.",
    flowNote: "Buradan sonra Ekipman veya Kesintiler modülü, personel kartının operasyonla nasıl bağlandığını göstermek için iyi bir devam.",
  },
  Kesintiler: {
    kicker: "Bordro On Hattı",
    title: "Kesinti akışı artık daha kontrollü",
    description:
      "Manuel ve otomatik kesintileri aynı panelde görmek, düzenlemek ve bordro etkisini kontrol etmek için kullanılır.",
    relatedLabels: ["Aylık Hakediş", "Personel", "Puantaj"],
    reviewPoints: [
      "Otomatik ve manuel kayıtlar listede karışmadan ayrisiyor mu bak.",
      "Miktar, neden ve personel bağlamı bir bakışta okunabiliyor mu incele.",
      "Kesinti kaydının bordro etkisi açık görünüyor mu kontrol et.",
    ],
    signal: "Bu modül, finansal hassasiyet ve operasyonel hız gerektiren kesinti kayıtlarını yönetir.",
    flowNote: "Kesintilerden sonra Aylık Hakediş ekranına geçmek, verinin sonuç katmanında nasıl yankılandığını göstermek için en net rota.",
  },
  Ekipman: {
    kicker: "Filo ve Zimmet",
    title: "Zimmet, satış ve box geri alım aynı hatta",
    description:
      "Ekipman kayıtlarını ofis yönetimi diliyle izlemek, düzenlemek ve kutu iadelerini birlikte görmek için tasarlandı.",
    relatedLabels: ["Satın Alma", "Kesintiler", "Sistem Kayıtları"],
    reviewPoints: [
      "Zimmet ve kutu geri alım akışlarının aynı kabukta karışmadan okunup okunmadığına bak.",
      "Maliyet, adet ve personel bağının birlikte net görünüp görünmediğini incele.",
      "Ofis yönetimi ağırlığı olan bir modül için yeterince güçlü duruyor mu kontrol et.",
    ],
    signal: "Bu modül, zimmet ve kutu iade kayıtlarını maliyet bilgisiyle birlikte takip eder.",
    flowNote: "Buradan sonra Satın Alma veya Sistem Kayıtları ekranına geçmek, ekipman hareketinin maliyet ve iz kaydı tarafını bağlar.",
  },
  "Aylık Hakediş": {
    kicker: "Finans Çekirdeği",
    title: "Net ödeme ve kesinti resmi buradan okunuyor",
    description:
      "Saat, paket, kesinti ve net ödeme dağılımını tek panelde daha kârlı ve daha hızlı analiz etmek için kuruldu.",
    relatedLabels: ["Kesintiler", "Raporlar", "Satın Alma"],
    reviewPoints: [
      "Özet kartların finansal resmi yeterince hızlı anlatıp anlatmadığına bak.",
      "Liste ve filtre tarafında ay bazlı okuma kolay mı incele.",
      "Kesinti ve net ödeme zinciri zihinde temiz kuruluyor mu kontrol et.",
    ],
    signal: "Bu ekran, ay kapanışında net ödeme ve kesinti kontrolü için kullanılır.",
    flowNote: "Bu duraktan sonra Raporlar modülü, rakamların daha geniş iş resmi içinde nasıl konumlandığını görmek için iyi bir devam.",
  },
  "Satın Alma": {
    kicker: "Ofis Maliyeti",
    title: "Fatura ve tedarik hareketi sade ama güçlü bir hatta",
    description:
      "Tedarikçiler, kalem bazlı alımlar ve birim maliyet resmi artık daha derli toplu bir satın alma panelinde.",
    relatedLabels: ["Ekipman", "Aylık Hakediş", "Raporlar"],
    reviewPoints: [
      "Tedarikçi, kalem ve fatura alanları arasında hiyerarşi net mi bak.",
      "Maliyet ekranının fazla muhasebesel görünmeden ciddi durup durmadığını incele.",
      "Liste ve form akışlarının aynı dilde kalıp kalmadığını kontrol et.",
    ],
    signal: "Satın alma modülü, tedarik ve fatura kayıtlarının maliyet takibini sağlar.",
    flowNote: "Bu ekrandan sonra Ekipman veya Raporlar rotası, satın alma verisinin nereye aktığını göstermek için iyi çalışıyor.",
  },
  "Satış": {
    kicker: "Ticari Akış",
    title: "Fırsat hattı ve teklif kayıtları aynı yerde",
    description:
      "Fırsat havuzu, teklif modeli, takip tarihi ve sorumlu kişi bilgileri tek satış ekranında toplanır.",
    relatedLabels: ["Raporlar", "Restoranlar", "Satın Alma"],
    reviewPoints: [
      "Fırsat hattında durum, teklif ve takip tarihi hızlı okunuyor mu bak.",
      "Teklif, takip tarihi ve sorumlu kişi gibi alanlar net okunuyor mu incele.",
      "Satış kayıtları operasyon kayıtlarından net ayrılıyor mu kontrol et.",
    ],
    signal: "Satış ekranı, fırsat ve teklif takibini canlı kayıtlarla yönetir.",
    flowNote: "Satış sonrası en iyi bağlantılar Restoranlar ve Raporlar; biri operasyon açılışını, diğeri ticari resmi devam ettiriyor.",
  },
  Restoranlar: {
    kicker: "Şube Katmanı",
    title: "Şube ve fiyat modeli kayıtları tek yerde",
    description:
      "Restoran kartları, aktiflik durumu, adres ve fiyat modeli bilgileri operasyonla birlikte takip edilir.",
    relatedLabels: ["Puantaj", "Satış", "Personel"],
    reviewPoints: [
      "Şube kartlarının kurumsal ama sıcak bir his verip vermediğine bak.",
      "Fiyat modeli ve aktiflik bilgisinin birlikte ne kadar net okunduğunu incele.",
      "Bu ekranın saha ile ticari katman arasında bir bağ kurup kurmadığına odaklan.",
    ],
    signal: "Restoranlar modülü, müşteri ve şube kayıtlarını operasyonla birlikte tutar.",
    flowNote: "Buradan sonra Satış veya Puantaj modülü, şube verisinin iki farklı yönde nasıl yaşadığını göstermek için iyi bir akış kurar.",
  },
  Raporlar: {
    kicker: "Karar Paneli",
    title: "Ciro, maliyet ve trend dili burada toparlanıyor",
    description:
      "Aylık ciro, maliyet ve operasyon etkilerini tek rapor panelinde okumayı kolaylaştırır.",
    relatedLabels: ["Aylık Hakediş", "Satış", "Satın Alma"],
    reviewPoints: [
      "Rapor özeti bir yöneticiye tek bakışta yön tayin ettiriyor mu bak.",
      "Trend, maliyet ve ciro dağılımı yeterince net görünüyor mu incele.",
      "Bu ekranın aylık rapor ihtiyacını tek yerde karşılayıp karşılamadığını kontrol et.",
    ],
    signal: "Raporlar modülü, aylık ciro, maliyet ve trend takibini özetler.",
    flowNote: "Raporlardan sonra Aylık Hakediş veya Satış ekranına dönerek kaynak kayıtları kontrol edilebilir.",
  },
  "Sistem Kayıtları": {
    kicker: "Admin Katmanı",
    title: "Kim ne yaptı sorusuna daha temiz cevap",
    description:
      "Denetim akışında filtreleme, akış takibi ve operasyonel şeffaflık aynı estetik kabukta.",
    relatedLabels: ["Ekipman", "Profil", "Genel Bakış"],
    reviewPoints: [
      "Denetim kayıtları ciddi ama sıkıcı olmayan bir tonda okunuyor mu bak.",
      "Filtre ve liste yoğunluğuna rağmen sayfa hâlâ sakin kalabiliyor mu incele.",
      "Bu ekran yönetici güveni veriyor mu kontrol et.",
    ],
    signal: "Bu modül, işlem geçmişini ve yönetici denetimini kayıt altında tutar.",
    flowNote: "Sistem Kayıtları sonrası Profil veya Genel Bakış rotası, yönetici akışlarını daha bütünlü görmek için mantıklı.",
  },
  Profil: {
    kicker: "Kimlik Katmanı",
    title: "Profil ve şifre işlemleri burada",
    description:
      "Kullanıcı bilgileri, oturum durumu ve şifre işlemleri bu alanda yönetilir.",
    relatedLabels: ["Genel Bakış", "Sistem Kayıtları"],
    reviewPoints: [
      "Giriş sonrası hesap bilgilerinin net ve güvenli göründüğünü kontrol et.",
      "Şifre değiştirme ve hesap bakımı akışlarının ürün kalitesine uyumuna odaklan.",
      "Şifre değiştirme akışı kolay tamamlanıyor mu kontrol et.",
    ],
    signal: "Profil ekranı, kullanıcının hesap güvenliği ve erişim bilgilerini güncel tutar.",
    flowNote: "Profil sonrası Genel Bakış veya Sistem Kayıtları rotası, kullanıcı ve yönetim katmanını birlikte okumak için iyi bir kapanış verir.",
  },
};

export function AppShell({
  children,
  activeItem = "Genel Bakış",
}: {
  children: React.ReactNode;
  activeItem?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();
  const previewMode = isPreviewPathname(pathname);

  const visibleItems = useMemo(() => {
    if (previewMode) {
      const previewItemMap: Record<string, string> = {
        "/": "/preview",
        "/announcements": "/preview/announcements",
        "/attendance": "/preview/attendance",
        "/personnel": "/preview/personnel",
        "/deductions": "/preview/deductions",
        "/equipment": "/preview/equipment",
        "/payroll": "/preview/payroll",
        "/purchases": "/preview/purchases",
        "/sales": "/preview/sales",
        "/restaurants": "/preview/restaurants",
        "/reports": "/preview/reports",
        "/audit": "/preview/audit",
        "/account": "/preview/account",
      };
      return sidebarItems
        .filter(
          (item) =>
            item.label === "Genel Bakış" ||
            item.label === "Puantaj" ||
            item.label === "Personel" ||
            item.label === "Sistem Kayıtları" ||
            item.label === "Kesintiler" ||
            item.label === "Ekipman" ||
            item.label === "Aylık Hakediş" ||
            item.label === "Satın Alma" ||
            item.label === "Satış" ||
            item.label === "Restoranlar" ||
            item.label === "Raporlar" ||
            item.label === "Profil",
        )
        .map(
          (item): SidebarItem => ({
            ...item,
            href: previewItemMap[item.href] ?? "/preview",
          }),
        );
    }
    return filterSidebarItems(user?.allowed_actions ?? []);
  }, [previewMode, user?.allowed_actions]);
  const canViewActiveItem = useMemo(
    () => visibleItems.some((item) => item.label === activeItem),
    [visibleItems, activeItem],
  );
  const previewMeta = previewMetaByLabel[activeItem] ?? previewMetaByLabel["Genel Bakış"];
  const previewRelatedItems = useMemo(
    () =>
      previewMeta.relatedLabels
        .map((label) => visibleItems.find((item) => item.label === label))
        .filter(Boolean) as SidebarItem[],
    [previewMeta.relatedLabels, visibleItems],
  );
  const previewActiveIndex = useMemo(
    () => visibleItems.findIndex((item) => item.label === activeItem),
    [activeItem, visibleItems],
  );
  const previewPreviousItem =
    previewActiveIndex > 0 ? visibleItems[previewActiveIndex - 1] : null;
  const previewNextItem =
    previewActiveIndex >= 0 && previewActiveIndex < visibleItems.length - 1
      ? visibleItems[previewActiveIndex + 1]
      : null;

  useEffect(() => {
    if (loading) {
      return;
    }
    if (!user) {
      const nextValue = pathname && pathname !== "/login" ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${nextValue}`);
      return;
    }
    if (user.must_change_password && pathname !== "/account") {
      router.replace("/account");
      return;
    }
    if (!canViewActiveItem) {
      router.replace(resolveDefaultPath(user.allowed_actions));
    }
  }, [canViewActiveItem, loading, pathname, router, user]);

  if (loading || !user || !canViewActiveItem) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          padding: "24px",
        }}
      >
        <div
          style={{
            width: "min(420px, 100%)",
            padding: "28px",
            borderRadius: "28px",
            background: "var(--surface-strong)",
            border: "1px solid var(--line)",
            boxShadow: "0 24px 60px rgba(22, 42, 74, 0.08)",
          }}
        >
          <div
            style={{
              height: "10px",
              borderRadius: "999px",
              background: "rgba(15, 95, 215, 0.1)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: "42%",
                height: "100%",
                background: "var(--accent)",
                borderRadius: "999px",
              }}
            />
          </div>
          <h2 style={{ margin: "18px 0 10px" }}>Oturum hazırlanıyor</h2>
          <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
            Yetki ve oturum bilgileri kontrol ediliyor. Hazır oldugunda seni doğrudan ilgili module alacagiz.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside
        className="app-shell__sidebar"
        style={{
          padding: "24px 20px 22px",
          borderRight: "1px solid rgba(255, 255, 255, 0.1)",
          background:
            "radial-gradient(circle at 18% 0%, rgba(72,198,181,0.32), transparent 28%), radial-gradient(circle at 96% 18%, rgba(255,184,107,0.22), transparent 24%), linear-gradient(180deg, #061624 0%, #082538 48%, #0f2635 100%)",
          color: "#f6fbff",
          backdropFilter: "blur(18px)",
          boxShadow: "inset -1px 0 0 rgba(255, 255, 255, 0.08)",
        }}
      >
        <div
          style={{
            padding: "16px",
            borderRadius: "26px",
            background: "linear-gradient(180deg, rgba(255,255,255,0.1), rgba(255,255,255,0.035))",
            border: "1px solid rgba(255,255,255,0.11)",
            boxShadow: "0 22px 46px rgba(0, 0, 0, 0.22)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <div
              aria-label="Çat Kapında"
              role="img"
              style={{
                width: "76px",
                height: "76px",
                flex: "0 0 auto",
                borderRadius: "24px",
                backgroundImage: "url('/catkapinda_logo.png')",
                backgroundRepeat: "no-repeat",
                backgroundPosition: "center",
                backgroundSize: "118%",
                filter: "drop-shadow(0 12px 22px rgba(0,0,0,0.28))",
              }}
            />
            <div style={{ display: "grid", gap: "3px" }}>
              <div
                style={{
                  color: "#ffffff",
                  fontWeight: 900,
                  fontSize: "1.12rem",
                  letterSpacing: "-0.02em",
                  lineHeight: 1,
                }}
              >
                Çat Kapında
              </div>
              <div
                style={{
                  width: "fit-content",
                  padding: "5px 9px",
                  borderRadius: "999px",
                  background: "rgba(72,198,181,0.16)",
                  color: "#aef3e9",
                  fontSize: "0.7rem",
                  fontWeight: 900,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                Operasyon CRM
              </div>
            </div>
          </div>
          <div
            style={{
              marginTop: "14px",
              color: "rgba(236, 248, 255, 0.76)",
              fontSize: "0.9rem",
              lineHeight: 1.55,
            }}
          >
            Şube, kadro, puantaj ve finans akışını tek yönetim masasında toparla.
          </div>
        </div>
        {previewMode ? (
          <div
            style={{
              padding: "14px 16px",
              borderRadius: "22px",
              border: "1px solid rgba(241,194,143,0.14)",
              background: "rgba(185, 116, 41, 0.08)",
              color: "#f8e2c0",
              lineHeight: 1.6,
              fontSize: "0.9rem",
              display: "grid",
              gap: "10px",
            }}
          >
            <div style={{ fontWeight: 800, color: "#fff1d8" }}>Tanıtım modundasın.</div>
            <div>Bu hat gerçek arka uç yerine örnek veriyle çalışır; kayıtlar kalıcı değildir.</div>
            <Link
              href="/login"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: "fit-content",
                padding: "10px 12px",
                borderRadius: "14px",
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#fff7ea",
                fontWeight: 800,
                textDecoration: "none",
              }}
            >
              Gerçek Girişe Dön
            </Link>
          </div>
        ) : null}
        <nav
          style={{
            display: "grid",
            gap: "8px",
          }}
        >
          {visibleItems.map((item) => {
            const isActive = item.label === activeItem;
            const accent = navAccentByLabel[item.label] ?? "#48c6b5";
            return (
              <Link
                key={item.label}
                href={item.href}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "11px",
                  minHeight: "44px",
                  padding: "11px 12px",
                  borderRadius: "16px",
                  border: isActive ? "1px solid rgba(255,255,255,0.18)" : "1px solid rgba(255,255,255,0.06)",
                  background: isActive
                    ? "linear-gradient(135deg, rgba(255,255,255,0.14), rgba(255,255,255,0.055))"
                    : "rgba(255, 255, 255, 0.025)",
                  color: isActive ? "#ffffff" : "rgba(236, 248, 255, 0.78)",
                  fontWeight: isActive ? 900 : 700,
                  boxShadow: isActive ? "0 16px 30px rgba(0, 0, 0, 0.18)" : "none",
                }}
              >
                <span
                  style={{
                    width: isActive ? "5px" : "4px",
                    alignSelf: "stretch",
                    minHeight: "24px",
                    borderRadius: "999px",
                    background: accent,
                    boxShadow: isActive ? `0 0 22px ${accent}` : "none",
                  }}
                />
                <span style={{ flex: 1 }}>{item.label}</span>
                {isActive ? (
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: "999px",
                      background: "rgba(255,255,255,0.1)",
                      color: "rgba(236,248,255,0.78)",
                      fontSize: "0.68rem",
                      fontWeight: 900,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                    }}
                  >
                    Aktif
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div
          style={{
            marginTop: "auto",
            paddingTop: "10px",
            display: "grid",
            gap: "10px",
          }}
        >
          <div
            style={{
              padding: "16px",
              borderRadius: "22px",
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255, 255, 255, 0.05)",
            }}
          >
            <div
              style={{
                fontWeight: 800,
                color: "#fff7ed",
              }}
            >
              {user.full_name}
            </div>
            <div
              style={{
                marginTop: "4px",
                color: "rgba(246, 239, 227, 0.66)",
                fontSize: "0.9rem",
              }}
            >
              {user.role_display}
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              void logout().then(() => router.replace("/login"));
            }}
            style={{
              padding: "13px 16px",
              borderRadius: "18px",
              border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255, 255, 255, 0.04)",
              color: "#fff4e5",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Oturumu Kapat
          </button>
        </div>
      </aside>
      <main
        className="app-shell__main"
        style={{
          padding: "30px",
        }}
      >
        <div
          style={{
            display: "grid",
            gap: "22px",
          }}
        >
          {previewMode ? (
            <section
              style={{
                padding: "22px 24px",
                borderRadius: "28px",
                border: "1px solid var(--line)",
                background:
                  "linear-gradient(180deg, rgba(255,253,248,0.98), rgba(246,240,229,0.96))",
                boxShadow: "var(--shadow-soft)",
                display: "grid",
                gap: "16px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: "16px",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "grid", gap: "8px", maxWidth: "72ch" }}>
                  <div
                    style={{
                      display: "inline-flex",
                      width: "fit-content",
                      padding: "6px 10px",
                      borderRadius: "999px",
                      background: "rgba(185,116,41,0.12)",
                      color: "var(--accent-strong)",
                      fontSize: "0.74rem",
                      fontWeight: 800,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    {previewMeta.kicker}
                  </div>
                  <h1
                    style={{
                      margin: 0,
                      fontFamily:
                        '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
                      fontSize: "clamp(1.8rem, 4vw, 2.8rem)",
                      lineHeight: 0.95,
                      letterSpacing: "-0.04em",
                    }}
                  >
                    {previewMeta.title}
                  </h1>
                  <p
                    style={{
                      margin: 0,
                      color: "var(--muted)",
                      lineHeight: 1.75,
                      fontSize: "0.97rem",
                    }}
                  >
                    {previewMeta.description}
                  </p>
                </div>

                <div
                  style={{
                    display: "grid",
                    gap: "10px",
                    minWidth: "260px",
                  }}
                >
                  <Link
                    href="/preview"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "12px",
                      padding: "12px 14px",
                      borderRadius: "18px",
                      background: "var(--surface-ink)",
                      color: "#fff7ea",
                      fontWeight: 800,
                      boxShadow: "var(--shadow-deep)",
                    }}
                  >
                    <span>Yerel Kontrol Merkezine Dön</span>
                    <span
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "999px",
                        display: "grid",
                        placeItems: "center",
                        background: "rgba(255,255,255,0.08)",
                      }}
                    >
                      H
                    </span>
                  </Link>
                  <div
                    style={{
                      display: "grid",
                      gap: "8px",
                    }}
                  >
                    <div
                      style={{
                        color: "var(--muted)",
                        fontSize: "0.74rem",
                        fontWeight: 800,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                      }}
                    >
                      İlgili Geçişler
                    </div>
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "8px",
                      }}
                    >
                      {previewRelatedItems.map((item) => (
                        <Link
                          key={item.label}
                          href={item.href}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "8px",
                            padding: "10px 12px",
                            borderRadius: "14px",
                            background: "rgba(24,40,59,0.06)",
                            border: "1px solid rgba(24,40,59,0.08)",
                            color: "var(--text)",
                            fontWeight: 700,
                            fontSize: "0.9rem",
                          }}
                        >
                          <span>{item.label}</span>
                          <span
                            style={{
                              width: "22px",
                              height: "22px",
                              borderRadius: "999px",
                              display: "grid",
                              placeItems: "center",
                              background: "rgba(185,116,41,0.12)",
                              color: "var(--accent-strong)",
                              fontSize: "0.72rem",
                              fontWeight: 900,
                            }}
                          >
                            {item.label.charAt(0)}
                          </span>
                        </Link>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(207,65,65,0.08)",
                    color: "#b73636",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Gerçek arka uç bağlı değil
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(185,116,41,0.1)",
                    color: "var(--accent-strong)",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Örnek verilerle gezilebilir yerel kontrol
                </span>
                <span
                  style={{
                    display: "inline-flex",
                    padding: "7px 12px",
                    borderRadius: "999px",
                    background: "rgba(24,40,59,0.08)",
                    color: "var(--text)",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Kayitlar kalıcı değil
                </span>
              </div>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <Link
                  href="/login"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "11px 14px",
                    borderRadius: "16px",
                    background: "var(--surface-ink)",
                    color: "#fff7ea",
                    fontWeight: 800,
                    textDecoration: "none",
                    boxShadow: "var(--shadow-deep)",
                  }}
                >
                  Gerçek Giriş Ekranina Git
                </Link>
                <Link
                  href="/status"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "11px 14px",
                    borderRadius: "16px",
                    border: "1px solid rgba(24,40,59,0.1)",
                    background: "rgba(255,255,255,0.72)",
                    color: "var(--text)",
                    fontWeight: 800,
                    textDecoration: "none",
                  }}
                >
                  Pilot Durumunu Kontrol Et
                </Link>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "12px",
                }}
              >
                <article
                  style={{
                    display: "grid",
                    gap: "10px",
                    padding: "16px 18px",
                    borderRadius: "20px",
                    border: "1px solid rgba(24,40,59,0.08)",
                    background: "rgba(255,255,255,0.72)",
                  }}
                >
                  <div
                    style={{
                      color: "var(--muted)",
                      fontSize: "0.74rem",
                      fontWeight: 800,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    Neye Bak
                  </div>
                  <div style={{ display: "grid", gap: "8px" }}>
                    {previewMeta.reviewPoints.map((point) => (
                      <div
                        key={point}
                        style={{
                          display: "grid",
                          gridTemplateColumns: "18px minmax(0, 1fr)",
                          gap: "8px",
                          color: "var(--text)",
                          lineHeight: 1.6,
                          fontSize: "0.93rem",
                        }}
                      >
                        <span
                          style={{
                            width: "18px",
                            height: "18px",
                            borderRadius: "999px",
                            display: "grid",
                            placeItems: "center",
                            background: "rgba(185,116,41,0.12)",
                            color: "var(--accent-strong)",
                            fontSize: "0.72rem",
                            fontWeight: 900,
                          }}
                        >
                          +
                        </span>
                        <span>{point}</span>
                      </div>
                    ))}
                  </div>
                </article>

                <article
                  style={{
                    display: "grid",
                    gap: "12px",
                    padding: "16px 18px",
                    borderRadius: "20px",
                    border: "1px solid rgba(24,40,59,0.08)",
                    background: "linear-gradient(180deg, rgba(24,40,59,0.96), rgba(34,53,76,0.94))",
                    color: "#fff7ea",
                    boxShadow: "var(--shadow-deep)",
                  }}
                >
                  <div
                    style={{
                      color: "rgba(255,247,234,0.64)",
                      fontSize: "0.74rem",
                      fontWeight: 800,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                    }}
                  >
                    Kritik Sinyal
                  </div>
                  <div
                    style={{
                      fontFamily:
                        '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
                      fontSize: "1.35rem",
                      lineHeight: 1.02,
                      letterSpacing: "-0.03em",
                    }}
                  >
                    {previewMeta.signal}
                  </div>
                  <div
                    style={{
                      color: "rgba(255,247,234,0.72)",
                      lineHeight: 1.65,
                      fontSize: "0.92rem",
                    }}
                  >
                    {previewMeta.flowNote}
                  </div>
                </article>

                <article
                  style={{
                    display: "grid",
                    gap: "12px",
                    padding: "16px 18px",
                    borderRadius: "20px",
                    border: "1px solid rgba(24,40,59,0.08)",
                    background: "rgba(255,255,255,0.72)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: "12px",
                      alignItems: "center",
                      flexWrap: "wrap",
                    }}
                  >
                    <div
                      style={{
                        color: "var(--muted)",
                        fontSize: "0.74rem",
                        fontWeight: 800,
                        letterSpacing: "0.08em",
                        textTransform: "uppercase",
                      }}
                    >
                      Akis Haritasi
                    </div>
                    <span
                      style={{
                        display: "inline-flex",
                        padding: "6px 10px",
                        borderRadius: "999px",
                        background: "rgba(15,95,215,0.08)",
                        color: "#0f5fd7",
                        fontSize: "0.8rem",
                        fontWeight: 800,
                      }}
                    >
                      Durak {Math.max(previewActiveIndex + 1, 1)} / {visibleItems.length}
                    </span>
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gap: "10px",
                    }}
                  >
                    {previewPreviousItem ? (
                      <Link
                        href={previewPreviousItem.href}
                        style={{
                          display: "grid",
                          gap: "4px",
                          padding: "12px 14px",
                          borderRadius: "16px",
                          background: "rgba(24,40,59,0.05)",
                          border: "1px solid rgba(24,40,59,0.08)",
                          color: "var(--text)",
                        }}
                      >
                        <span
                          style={{
                            color: "var(--muted)",
                            fontSize: "0.73rem",
                            fontWeight: 800,
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                          }}
                        >
                          Onceki Durak
                        </span>
                        <span style={{ fontWeight: 800 }}>{previewPreviousItem.label}</span>
                      </Link>
                    ) : null}
                    {previewNextItem ? (
                      <Link
                        href={previewNextItem.href}
                        style={{
                          display: "grid",
                          gap: "4px",
                          padding: "12px 14px",
                          borderRadius: "16px",
                          background: "rgba(185,116,41,0.08)",
                          border: "1px solid rgba(185,116,41,0.18)",
                          color: "var(--text)",
                        }}
                      >
                        <span
                          style={{
                            color: "var(--muted)",
                            fontSize: "0.73rem",
                            fontWeight: 800,
                            textTransform: "uppercase",
                            letterSpacing: "0.08em",
                          }}
                        >
                          Sonraki Durak
                        </span>
                        <span style={{ fontWeight: 800 }}>{previewNextItem.label}</span>
                      </Link>
                    ) : null}
                    {!previewPreviousItem && !previewNextItem ? (
                      <div
                        style={{
                          padding: "12px 14px",
                          borderRadius: "16px",
                          background: "rgba(24,40,59,0.05)",
                          color: "var(--muted)",
                          lineHeight: 1.6,
                        }}
                      >
                        Bu preview rotasi tekil bir kesit değil; yandaki ilgili gecisler ile keşif akışını derinlestirebilirsin.
                      </div>
                    ) : null}
                  </div>
                </article>
              </div>
            </section>
          ) : null}

          {children}
        </div>
      </main>
    </div>
  );
}
