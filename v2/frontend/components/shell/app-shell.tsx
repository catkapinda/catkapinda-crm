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

const previewMetaByLabel: Record<string, PreviewMeta> = {
  "Genel Bakış": {
    kicker: "Preview Hub",
    title: "Tum v2 deneyimini tek merkezden oku",
    description:
      "Preview hattinin omurgasi burada. Modulleri akisa gore ayiriyor, son sinyalleri topluyor ve nereden baslanacagini netlestiriyor.",
    relatedLabels: ["Puantaj", "Satış", "Ekipman"],
    reviewPoints: [
      "Saha, ticari ve kontrol katmanlarinin ayni merkezde nasil bulustuguna bak.",
      "Recent activity akisinin moduller arasi hikaye kurup kurmadigini kontrol et.",
      "Hangi module once girmenin daha dogal hissettirdigine odaklan.",
    ],
    signal: "Bu yuzey artik sadece dashboard degil, tum preview deneyiminin ana komuta masasi gibi davraniyor.",
    flowNote: "Bu noktadan sonra saha omurgasina gecmek icin once Puantaj, finans resmi icin Satış veya Ekipman iyi bir devam rotasi.",
  },
  "Puantaj": {
    kicker: "Saha Omurgasi",
    title: "Gunluk puantaj akisi yeni katta",
    description:
      "Vardiya, destek gecisi ve aylik kayit temizligi gibi operasyonun en sik dokunulan islerini hizli gozlemlemek icin hazir.",
    relatedLabels: ["Personel", "Kesintiler", "Restoranlar"],
    reviewPoints: [
      "Gunluk giris akisinda yogun kullanima uygun ritim hissediliyor mu bak.",
      "Liste, filtre ve tehlikeli aksiyonlarin ayirt edilebilirligine odaklan.",
      "Saha operasyoni icin hiz, netlik ve kontrol dengesi kuruldu mu kontrol et.",
    ],
    signal: "En sik kullanilan modul oldugu icin tasarim dili burada agirlik ve hiz arasinda dengeleniyor.",
    flowNote: "Puantajdan sonra Personel veya Kesintiler yuzeyine gecmek, karar zincirinin tutarliligini daha iyi gosterir.",
  },
  Personel: {
    kicker: "Kadro Yonetimi",
    title: "Kadro kartlari ve saha dagilimi burada toparlaniyor",
    description:
      "Kart acma, durum degistirme ve restoran dagilimi yeni dilde daha okunur bir yuzeye donusuyor.",
    relatedLabels: ["Puantaj", "Kesintiler", "Ekipman"],
    reviewPoints: [
      "Kart yogunlugu yuksek olsa bile sayfa nefes aliyor mu incele.",
      "Aktif-pasif, restoran dagilimi ve iletisim bilgileri kolay taraniyor mu bak.",
      "Yeni tasarim yoneticiye daha guven veren bir kontrol hissi veriyor mu kontrol et.",
    ],
    signal: "Personel ekraninda premium his, bilgi kalabaligini daha sakin ve hiyerarsik bir dilde eritmekten geliyor.",
    flowNote: "Buradan sonra Ekipman veya Kesintiler modulu, personel kartinin operasyonla nasil baglandigini gostermek icin iyi bir devam.",
  },
  Kesintiler: {
    kicker: "Bordro On Hatti",
    title: "Kesinti akisi artik daha kontrollu",
    description:
      "Manuel ve otomatik kesintileri ayni panelde gormek, duzenlemek ve payroll etkisini hissetmek icin acik.",
    relatedLabels: ["Aylık Hakediş", "Personel", "Puantaj"],
    reviewPoints: [
      "Otomatik ve manuel kayitlar ayni yuzeyde karismadan ayrisiyor mu bak.",
      "Miktar, neden ve personel baglami bir bakista okunabiliyor mu incele.",
      "Kesinti akisinin bordroya giden karar hissini verip vermedigine odaklan.",
    ],
    signal: "Bu moduldaki kalite hissi, finansal hassasiyet ile operasyonel hiz arasindaki dengeyi dogru kurdugunda gucleniyor.",
    flowNote: "Kesintilerden sonra Aylik Hakedis ekranina gecmek, verinin sonuc katmaninda nasil yankilandigini gostermek icin en net rota.",
  },
  Ekipman: {
    kicker: "Filo ve Zimmet",
    title: "Zimmet, satis ve box geri alim ayni hatta",
    description:
      "Ekipman kayitlarini backoffice diliyle izlemek, duzenlemek ve box iadelerini birlikte gormek icin tasarlandi.",
    relatedLabels: ["Satın Alma", "Kesintiler", "Sistem Kayıtları"],
    reviewPoints: [
      "Zimmet ve box geri alim akislarinin ayni kabukta karismadan okunup okunmadigina bak.",
      "Maliyet, adet ve personel baginin birlikte yeterince net hissedilip hissedilmedigini incele.",
      "Backoffice agirligi olan bir modul icin yeterince premium duruyor mu kontrol et.",
    ],
    signal: "Bu yuzey, operasyonel agirligi yuksek alanlarda bile arayuzun koleksiyon sayfasi gibi duz degil, niyetli bir panel gibi davranabilecegini gosteriyor.",
    flowNote: "Buradan sonra Satin Alma veya Sistem Kayitlari ekranina gecmek, ekipman hareketinin maliyet ve iz kaydi tarafini baglar.",
  },
  "Aylık Hakediş": {
    kicker: "Finans Cekirdegi",
    title: "Net odeme ve kesinti resmi buradan okunuyor",
    description:
      "Saat, paket, kesinti ve net odeme dagilimini tek panelde daha karli ve daha hizli analiz etmek icin kuruldu.",
    relatedLabels: ["Kesintiler", "Raporlar", "Satın Alma"],
    reviewPoints: [
      "Ozet kartlarin finansal resmi yeterince hizli anlatip anlatmadigina bak.",
      "Liste ve filtre tarafinda ay bazli okuma kolay mi incele.",
      "Kesinti ve net odeme zinciri zihinde temiz kuruluyor mu kontrol et.",
    ],
    signal: "Bordroya yakin ekranlarda tasarimin amaci gorsel gosteri degil, karar kalitesini yukseltmek.",
    flowNote: "Bu duraktan sonra Raporlar modulu, rakamlarin daha genis is resmi icinde nasil konumlandigini gormek icin iyi bir devam.",
  },
  "Satın Alma": {
    kicker: "Backoffice Maliyet",
    title: "Fatura ve tedarik hareketi sade ama guclu bir hatta",
    description:
      "Tedarikciler, kalem bazli alimlar ve birim maliyet resmi artik daha derli toplu bir satin alma panelinde.",
    relatedLabels: ["Ekipman", "Aylık Hakediş", "Raporlar"],
    reviewPoints: [
      "Tedarikci, kalem ve fatura alanlari arasinda hiyerarsi net mi bak.",
      "Maliyet ekraninin fazla muhasebesel gorunmeden ciddi durup durmadigina incele.",
      "Liste ve form akislarinin ayni dilde kalip kalmadigini kontrol et.",
    ],
    signal: "Satin alma modulu, sessiz ama guclu bir backoffice tasarim dilinin neleri iyilestirebildigini gosteren kritik yuzeylerden biri.",
    flowNote: "Bu ekrandan sonra Ekipman veya Raporlar rotasi, satin alma verisinin nereye aktigini gostermek icin iyi calisiyor.",
  },
  "Satış": {
    kicker: "Ticari Akis",
    title: "Pipeline ve teklif hikayesi daha ikna edici bir yuzeyde",
    description:
      "Firsat havuzu, teklif modeli ve takip aksiyonlari daha editoryal bir satista bulusuyor.",
    relatedLabels: ["Raporlar", "Restoranlar", "Satın Alma"],
    reviewPoints: [
      "Pipeline enerjisinin daha canli ve premium hissedilip hissedilmedigine bak.",
      "Teklif, takip tarihi ve sorumlu sahibi gibi alanlar net okunuyor mu incele.",
      "Ticari modullerin operasyon modullerinden farkli bir enerji tasiyip tasimadigini kontrol et.",
    ],
    signal: "Satis ekraninda hedef, kurumsal ama heyecansiz bir tablo yerine hareket hissi veren bir ticari panel kurmak.",
    flowNote: "Satis sonrasi en iyi baglantilar Restoranlar ve Raporlar; biri operasyon acilisini, digeri ticari resmi devam ettiriyor.",
  },
  Restoranlar: {
    kicker: "Sube Katmani",
    title: "Sube ve fiyat modeli kararlari daha net okunuyor",
    description:
      "Restoran kartlari, aktiflik ve fiyat yapilari operasyonla daha bagli bir yuzeyde incelenebiliyor.",
    relatedLabels: ["Puantaj", "Satış", "Personel"],
    reviewPoints: [
      "Sube kartlarinin kurumsal ama sicak bir his verip vermedigine bak.",
      "Fiyat modeli ve aktiflik bilgisinin birlikte ne kadar net okundugunu incele.",
      "Bu ekranin saha ile ticari katman arasinda bir bag kurup kurmadigina odaklan.",
    ],
    signal: "Restoranlar modulu, CRM tarafinin yalnizca ic operasyon degil, musteri yuzlu karar katmani da oldugunu hissettiriyor.",
    flowNote: "Buradan sonra Satis veya Puantaj modulu, sube verisinin iki farkli yonde nasil yasadigini gostermek icin iyi bir akis kurar.",
  },
  Raporlar: {
    kicker: "Karar Paneli",
    title: "Ciro, maliyet ve trend dili burada toparlaniyor",
    description:
      "Aylik resmi daha premium bir rapor deneyimine cekiyor; ticari ve operasyonel etkileri tek bakista okumayi kolaylastiriyor.",
    relatedLabels: ["Aylık Hakediş", "Satış", "Satın Alma"],
    reviewPoints: [
      "Rapor ozeti bir yoneticiye tek bakista yon tayin ettiriyor mu bak.",
      "Trend, maliyet ve ciro ritmi yeterince editoryal hissediyor mu incele.",
      "Bu ekranin tum sistemin karar katmani gibi davranip davranmadigini kontrol et.",
    ],
    signal: "Raporlar modulu, yeni dilin en dogrudan 'premium urun' hissini uretebilecegi katmanlardan biri.",
    flowNote: "Raporlardan sonra Aylik Hakedis veya Satis ekranina donmek, karar verisinin kaynak akislarla uyumunu gosterir.",
  },
  "Sistem Kayıtları": {
    kicker: "Admin Katmani",
    title: "Kim ne yapti sorusuna daha temiz cevap",
    description:
      "Audit akisinda filtreleme, akis takibi ve operasyonel seffaflik ayni estetik kabukta.",
    relatedLabels: ["Ekipman", "Profil", "Genel Bakış"],
    reviewPoints: [
      "Audit kayitlari ciddi ama sikici olmayan bir tonda okunuyor mu bak.",
      "Filtre ve liste yogunlugune ragmen sayfa hala sakin kalabiliyor mu incele.",
      "Bu ekran admin guveni veriyor mu kontrol et.",
    ],
    signal: "Bu yuzey, sistemin guven ve izlenebilirlik tarafini tasarim kalitesinden odun vermeden sunuyor.",
    flowNote: "Sistem Kayitlari sonrasi Profil veya Genel Bakis rotasi, yonetici akislarini daha butunlu gormek icin mantikli.",
  },
  Profil: {
    kicker: "Kimlik Katmani",
    title: "Profil ve sifre akisi de preview deneyimine dahil",
    description:
      "Sadece operasyon degil, kullanicinin uygulama ile kurdugu kisiel temas da yeni dilde gorunur halde.",
    relatedLabels: ["Genel Bakış", "Sistem Kayıtları"],
    reviewPoints: [
      "Giris sonrasi en kisisel ekranin yeterince sakin ve guvenli hissedip hissetmedigine bak.",
      "Sifre degistirme ve hesap bakimi akislarinin urun kalitesine uyumuna odaklan.",
      "Yardimci ama ikincil bir ekran olmasina ragmen karakterini koruyor mu kontrol et.",
    ],
    signal: "Profil ekraninda kalite hissi, kullanicinin sistemle bire bir temas ettigi alanlarda da ayni estetik omurganin korunmasindan geliyor.",
    flowNote: "Profil sonrasi Genel Bakis veya Sistem Kayitlari rotasi, kullanici ve yonetim katmanini birlikte okumak icin iyi bir kapanis verir.",
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
          <h2 style={{ margin: "18px 0 10px" }}>v2 oturumu aciliyor</h2>
          <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.7 }}>
            Yetki ve oturum bilgileri kontrol ediliyor. Hazir oldugunda seni dogrudan ilgili module alacagiz.
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
          padding: "28px 24px 24px",
          borderRight: "1px solid rgba(255, 255, 255, 0.08)",
          background:
            "linear-gradient(180deg, rgba(19, 32, 48, 0.98) 0%, rgba(24, 40, 59, 0.96) 42%, rgba(37, 55, 77, 0.96) 100%)",
          color: "#f6efe3",
          backdropFilter: "blur(18px)",
          boxShadow: "inset -1px 0 0 rgba(255, 255, 255, 0.06)",
        }}
      >
        <div
          style={{
            padding: "18px 18px 16px",
            borderRadius: "28px",
            background: "linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02))",
            border: "1px solid rgba(255,255,255,0.08)",
            boxShadow: "0 20px 38px rgba(0, 0, 0, 0.18)",
          }}
        >
          <div
            style={{
              display: "inline-flex",
              padding: "6px 10px",
              borderRadius: "999px",
              background: "rgba(185, 116, 41, 0.18)",
              color: "#f1c28f",
              fontSize: "0.72rem",
              fontWeight: 800,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            {previewMode ? "v2 Preview" : "v2 Pilot"}
          </div>
          <div
            style={{
              marginTop: "16px",
              color: "#fff7ed",
              fontWeight: 900,
              fontSize: "1.85rem",
              letterSpacing: "-0.03em",
              lineHeight: 0.95,
              fontFamily:
                '"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif',
            }}
          >
            Cat Kapinda CRM
          </div>
          <div
            style={{
              marginTop: "10px",
              color: "rgba(246, 239, 227, 0.72)",
              fontSize: "0.92rem",
              lineHeight: 1.6,
            }}
          >
            Operasyonun gunluk nabzi, karar panelleri ve saha akisi tek kabukta.
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
            }}
          >
            Preview modundayiz. Bu hat backend beklemeden tasarim yuzeylerini gezmek icin acik.
          </div>
        ) : null}
        <nav
          style={{
            display: "grid",
            gap: "10px",
          }}
        >
          {visibleItems.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              style={{
                padding: "14px 16px",
                borderRadius: "20px",
                border:
                  item.label === activeItem
                    ? "1px solid rgba(241, 194, 143, 0.4)"
                    : "1px solid rgba(255, 255, 255, 0.08)",
                background:
                  item.label === activeItem
                    ? "linear-gradient(135deg, rgba(185, 116, 41, 0.24), rgba(255,255,255,0.08))"
                    : "rgba(255, 255, 255, 0.03)",
                color: item.label === activeItem ? "#fff4e5" : "rgba(246, 239, 227, 0.84)",
                fontWeight: item.label === activeItem ? 800 : 700,
                boxShadow:
                  item.label === activeItem ? "0 18px 34px rgba(0, 0, 0, 0.16)" : "none",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "12px",
                }}
              >
                <span>{item.label}</span>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minWidth: "30px",
                    height: "30px",
                    borderRadius: "12px",
                    background:
                      item.label === activeItem
                        ? "rgba(255,255,255,0.14)"
                        : "rgba(255,255,255,0.06)",
                    fontSize: "0.76rem",
                    fontWeight: 900,
                  }}
                >
                  {item.label.charAt(0)}
                </span>
              </div>
            </Link>
          ))}
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
                    <span>Preview Hub'a Don</span>
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
                      Ilgili Gecisler
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
                    background: "rgba(15,95,215,0.08)",
                    color: "#0f5fd7",
                    fontSize: "0.82rem",
                    fontWeight: 800,
                  }}
                >
                  Backend bagimsiz preview akisi acik
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
                  Mock veri ile gezilebilir durum
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
                  Aktif sayfa: {activeItem}
                </span>
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
                        Bu preview rotasi tekil bir kesit degil; yandaki ilgili gecisler ile kesif akisini derinlestirebilirsin.
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
