export type SidebarItem = {
  label: string;
  href: string;
  action?: string;
};

const temporarilyHiddenSidebarLabels = new Set(["Duyurular", "Sistem Kayıtları"]);

const allSidebarItems: SidebarItem[] = [
  { label: "Genel Bakış", href: "/", action: "dashboard.view" },
  { label: "Duyurular", href: "/announcements", action: "announcements.view" },
  { label: "Sistem Kayıtları", href: "/audit", action: "audit.view" },
  { label: "Puantaj", href: "/attendance", action: "attendance.view" },
  { label: "Personel", href: "/personnel", action: "personnel.view" },
  { label: "Kesintiler", href: "/deductions", action: "deduction.view" },
  { label: "Ekipman", href: "/equipment", action: "equipment.view" },
  { label: "Aylık Hakediş", href: "/payroll", action: "payroll.view" },
  { label: "Satın Alma", href: "/purchases", action: "purchase.view" },
  { label: "Satış", href: "/sales", action: "sales.view" },
  { label: "Restoranlar", href: "/restaurants", action: "restaurant.view" },
  { label: "Raporlar", href: "/reports", action: "reporting.view" },
  { label: "Profil", href: "/account" },
];

export const sidebarItems: SidebarItem[] = allSidebarItems.filter(
  (item) => !temporarilyHiddenSidebarLabels.has(item.label),
);

export function filterSidebarItems(allowedActions: string[]) {
  return sidebarItems.filter((item) => !item.action || allowedActions.includes(item.action));
}

export function resolveDefaultPath(allowedActions: string[]) {
  return filterSidebarItems(allowedActions)[0]?.href ?? "/login";
}
