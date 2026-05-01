"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "../auth/auth-provider";
import { AuthSessionLoadingScreen } from "../auth/auth-session-loading-screen";
import type { SidebarItem } from "../../lib/navigation";
import { filterSidebarItems, resolveDefaultPath, sidebarItems } from "../../lib/navigation";
import { isPreviewPathname } from "../../lib/preview";
import styles from "./app-shell.module.css";

type NavGroup = {
  label: string;
  items: string[];
};

type IconName =
  | "home"
  | "attendance"
  | "personnel"
  | "payroll"
  | "deductions"
  | "equipment"
  | "restaurants"
  | "invoices"
  | "purchases"
  | "sales"
  | "reports"
  | "profile"
  | "search"
  | "logout"
  | "menu"
  | "close"
  | "chevron";

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Ana Menü",
    items: ["Genel Bakış", "Puantaj", "Personel", "Aylık Hakediş"],
  },
  {
    label: "Operasyon",
    items: ["Kesintiler", "Ekipman", "Restoranlar"],
  },
  {
    label: "Finans",
    items: ["Faturalar", "Satın Alma", "Satış"],
  },
  {
    label: "Analiz",
    items: ["Raporlar"],
  },
  {
    label: "Hesap",
    items: ["Profil"],
  },
];

const iconNameByLabel: Record<string, IconName> = {
  "Genel Bakış": "home",
  Puantaj: "attendance",
  Personel: "personnel",
  "Aylık Hakediş": "payroll",
  Kesintiler: "deductions",
  Ekipman: "equipment",
  Restoranlar: "restaurants",
  Faturalar: "invoices",
  "Satın Alma": "purchases",
  Satış: "sales",
  Raporlar: "reports",
  Profil: "profile",
};

function ShellIcon({
  name,
  className,
}: {
  name: IconName;
  className?: string;
}) {
  const commonProps = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.9,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    className,
    "aria-hidden": true,
  };

  switch (name) {
    case "home":
      return (
        <svg {...commonProps}>
          <path d="M4 10.5 12 4l8 6.5" />
          <path d="M6.5 9.5v9h11v-9" />
        </svg>
      );
    case "attendance":
      return (
        <svg {...commonProps}>
          <rect x="4" y="5" width="16" height="15" rx="3" />
          <path d="M8 3.5v3" />
          <path d="M16 3.5v3" />
          <path d="M4 9.5h16" />
          <path d="m9.5 14 1.5 1.5 3.5-3.5" />
        </svg>
      );
    case "personnel":
      return (
        <svg {...commonProps}>
          <path d="M16 19v-1.5A3.5 3.5 0 0 0 12.5 14h-1A3.5 3.5 0 0 0 8 17.5V19" />
          <circle cx="12" cy="8.5" r="3.5" />
        </svg>
      );
    case "payroll":
      return (
        <svg {...commonProps}>
          <path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H18a2 2 0 0 1 2 2v1.5H8.5A2.5 2.5 0 0 0 6 11v2a2.5 2.5 0 0 0 2.5 2.5H20V17a2 2 0 0 1-2 2H5.5A2.5 2.5 0 0 1 3 16.5z" />
          <path d="M20 8.5h-11A2.5 2.5 0 0 0 6.5 11v2A2.5 2.5 0 0 0 9 15.5h11A1.5 1.5 0 0 0 21.5 14V10A1.5 1.5 0 0 0 20 8.5Z" />
          <circle cx="16.5" cy="12" r="1" fill="currentColor" stroke="none" />
        </svg>
      );
    case "deductions":
      return (
        <svg {...commonProps}>
          <circle cx="12" cy="12" r="8.5" />
          <path d="M8.5 12h7" />
        </svg>
      );
    case "equipment":
      return (
        <svg {...commonProps}>
          <path d="M12 3.5 19 7v10l-7 3.5L5 17V7z" />
          <path d="m5 7 7 3.5L19 7" />
          <path d="M12 10.5V20.5" />
        </svg>
      );
    case "restaurants":
      return (
        <svg {...commonProps}>
          <path d="M4 10h16" />
          <path d="M6 10v8.5" />
          <path d="M18 10v8.5" />
          <path d="M8 18.5V14h4v4.5" />
          <path d="M5 10 6.5 4h11L19 10" />
        </svg>
      );
    case "invoices":
      return (
        <svg {...commonProps}>
          <path d="M6 3.5h9l3 3V20H6z" />
          <path d="M15 3.5v4h4" />
          <path d="M9 11h6" />
          <path d="M9 15h6" />
        </svg>
      );
    case "purchases":
      return (
        <svg {...commonProps}>
          <circle cx="9" cy="19" r="1.5" />
          <circle cx="17" cy="19" r="1.5" />
          <path d="M4 5h2l1.6 8.5h9.7l1.7-6.5H7.2" />
        </svg>
      );
    case "sales":
      return (
        <svg {...commonProps}>
          <path d="m4.5 16 4.5-4.5 3 3L19.5 7" />
          <path d="M15.5 7h4v4" />
        </svg>
      );
    case "reports":
      return (
        <svg {...commonProps}>
          <path d="M5.5 19V11" />
          <path d="M10.5 19V7" />
          <path d="M15.5 19v-5" />
          <path d="M20.5 19V4" />
        </svg>
      );
    case "profile":
      return (
        <svg {...commonProps}>
          <circle cx="12" cy="8.5" r="3.5" />
          <path d="M6 19a6 6 0 0 1 12 0" />
        </svg>
      );
    case "search":
      return (
        <svg {...commonProps}>
          <circle cx="10.5" cy="10.5" r="5.5" />
          <path d="m15 15 4 4" />
        </svg>
      );
    case "logout":
      return (
        <svg {...commonProps}>
          <path d="M10 4.5H7A2.5 2.5 0 0 0 4.5 7v10A2.5 2.5 0 0 0 7 19.5h3" />
          <path d="M14 16.5 19 12l-5-4.5" />
          <path d="M19 12H10" />
        </svg>
      );
    case "menu":
      return (
        <svg {...commonProps}>
          <path d="M4 7h16" />
          <path d="M4 12h16" />
          <path d="M4 17h16" />
        </svg>
      );
    case "close":
      return (
        <svg {...commonProps}>
          <path d="m6 6 12 12" />
          <path d="M18 6 6 18" />
        </svg>
      );
    case "chevron":
      return (
        <svg {...commonProps}>
          <path d="m9 6 6 6-6 6" />
        </svg>
      );
    default:
      return null;
  }
}

function getInitials(name: string) {
  return name
    .split(" ")
    .map((part) => part.trim().charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function groupSidebarItems(items: SidebarItem[]) {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items
      .map((label) => items.find((item) => item.label === label))
      .filter(Boolean) as SidebarItem[],
  })).filter((group) => group.items.length > 0);
}

function renderBrand() {
  return (
    <div className={styles.brand}>
      <div className={styles.brandMark} aria-hidden="true">
        <span className={styles.brandCubeOuter} />
        <span className={styles.brandCubeInner} />
      </div>
      <div className={styles.brandCopy}>
        <strong>ÇAT KAPINDA</strong>
        <span>CRM</span>
      </div>
    </div>
  );
}

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
  const [drawerOpen, setDrawerOpen] = useState(false);
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
        "/invoices": "/preview/reports",
        "/reports": "/preview/reports",
        "/audit": "/preview/audit",
        "/account": "/preview/account",
      };
      return sidebarItems.map((item) => ({
        ...item,
        href: previewItemMap[item.href] ?? "/preview",
      }));
    }

    return filterSidebarItems(user?.allowed_actions ?? []);
  }, [previewMode, user?.allowed_actions]);

  const groupedItems = useMemo(() => groupSidebarItems(visibleItems), [visibleItems]);

  const canViewActiveItem = useMemo(
    () => visibleItems.some((item) => item.label === activeItem),
    [visibleItems, activeItem],
  );

  useEffect(() => {
    if (loading) {
      return;
    }
    if (!user) {
      const nextValue = pathname && pathname !== "/login" ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${nextValue}`);
      return;
    }
    if (user.must_change_password && user.role !== "mobile_ops" && pathname !== "/account") {
      router.replace("/account");
      return;
    }
    if (!canViewActiveItem) {
      router.replace(resolveDefaultPath(user.allowed_actions));
    }
  }, [canViewActiveItem, loading, pathname, router, user]);

  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  if (loading || !user || !canViewActiveItem) {
    return <AuthSessionLoadingScreen />;
  }

  const renderSidebarContent = ({ includeBrand = true }: { includeBrand?: boolean } = {}) => (
    <div className={styles.sidebarContent}>
      <div className={styles.sidebarTop}>
        {includeBrand ? renderBrand() : null}
        <button type="button" className={styles.searchShell} aria-label="Ara">
          <span className={styles.searchIconWrap}>
            <ShellIcon name="search" className={styles.searchIcon} />
          </span>
          <span className={styles.searchPlaceholder}>Ara...</span>
          <span className={styles.searchShortcut}>⌘K</span>
        </button>
      </div>

      <div className={styles.sidebarNav}>
        {groupedItems.map((group) => (
          <section key={group.label} className={styles.navGroup}>
            <div className={styles.navGroupLabel}>{group.label}</div>
            <div className={styles.navList}>
              {group.items.map((item) => {
                const isActive = item.label === activeItem;
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className={`${styles.navItem} ${isActive ? styles.navItemActive : ""}`}
                  >
                    <span className={styles.navItemAccent} aria-hidden="true" />
                    <span className={styles.navItemIconBadge}>
                      <ShellIcon
                        name={iconNameByLabel[item.label] ?? "home"}
                        className={styles.navItemIcon}
                      />
                    </span>
                    <span className={styles.navItemLabel}>{item.label}</span>
                    {isActive ? <span className={styles.navItemDot} aria-hidden="true" /> : null}
                  </Link>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      <div className={styles.sidebarFooter}>
        <button type="button" className={styles.userCard}>
          <span className={styles.userAvatar}>{getInitials(user.full_name)}</span>
          <span className={styles.userCopy}>
            <strong>{user.full_name}</strong>
            <span>{user.role_display}</span>
          </span>
          <ShellIcon name="chevron" className={styles.userChevron} />
        </button>
        <button
          type="button"
          className={styles.logoutButton}
          onClick={() => {
            void logout().then(() => router.replace("/login"));
          }}
        >
          <ShellIcon name="logout" className={styles.logoutIcon} />
          <span>Oturumu Kapat</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>{renderSidebarContent()}</aside>

      {drawerOpen ? (
        <div className={styles.drawerLayer} role="presentation" onClick={() => setDrawerOpen(false)}>
          <aside
            className={styles.drawer}
            role="dialog"
            aria-modal="true"
            aria-label="Navigasyon menüsü"
            onClick={(event) => event.stopPropagation()}
          >
            <div className={styles.drawerHeader}>
              {renderBrand()}
              <button
                type="button"
                className={styles.drawerClose}
                onClick={() => setDrawerOpen(false)}
                aria-label="Menüyü kapat"
              >
                <ShellIcon name="close" className={styles.drawerCloseIcon} />
              </button>
            </div>
            {renderSidebarContent({ includeBrand: false })}
          </aside>
        </div>
      ) : null}

      <main className={styles.main}>
        <div className={styles.mobileBar}>
          <button
            type="button"
            className={styles.mobileMenuButton}
            onClick={() => setDrawerOpen(true)}
            aria-label="Menüyü aç"
          >
            <ShellIcon name="menu" className={styles.mobileMenuIcon} />
          </button>
          <div className={styles.mobileBarCopy}>
            <strong>{activeItem}</strong>
            <span>Çat Kapında CRM</span>
          </div>
        </div>

        {previewMode ? (
          <section className={styles.previewBanner}>
            <div className={styles.previewBadge}>Preview</div>
            <p>Bu rota örnek veriyle çalışır. Kayıtlar kalıcı değildir.</p>
            <Link href="/login" className={styles.previewLink}>
              Gerçek girişe dön
            </Link>
          </section>
        ) : null}

        {children}
      </main>
    </div>
  );
}
