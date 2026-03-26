export type SidebarItem = {
  label: string;
  href: string;
  action?: string;
};

export const sidebarItems: SidebarItem[] = [
  { label: "Genel Bakış", href: "/", action: "dashboard.view" },
  { label: "Puantaj", href: "/attendance", action: "attendance.view" },
  { label: "Personel", href: "/personnel", action: "personnel.view" },
  { label: "Kesintiler", href: "/deductions", action: "deduction.view" },
  { label: "Satış", href: "/sales", action: "sales.view" },
  { label: "Restoranlar", href: "/restaurants", action: "restaurant.view" },
  { label: "Raporlar", href: "/reports", action: "reporting.view" },
];

export function filterSidebarItems(allowedActions: string[]) {
  return sidebarItems.filter((item) => !item.action || allowedActions.includes(item.action));
}

export function resolveDefaultPath(allowedActions: string[]) {
  return filterSidebarItems(allowedActions)[0]?.href ?? "/login";
}
