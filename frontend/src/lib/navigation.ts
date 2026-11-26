import {
  FileSearch,
  Gauge,
  History,
  LayoutDashboard,
  ListChecks,
  Settings,
  Shield,
  type LucideIcon,
} from "lucide-react";

export type NavHref =
  | "/"
  | "/cliff-guard"
  | "/bill-auditor"
  | "/meter-readings"
  | "/action-plan"
  | "/history"
  | "/settings";

export type NavigationItem = {
  href: NavHref;
  label: string;
  shortLabel: string;
  description: string;
  icon: LucideIcon;
  mobile: "tab" | "more";
};

export const navigation: readonly NavigationItem[] = [
  {
    href: "/",
    label: "Overview",
    shortLabel: "Overview",
    description: "Sample household position for the illustrated November cycle.",
    icon: LayoutDashboard,
    mobile: "tab",
  },
  {
    href: "/cliff-guard",
    label: "Cliff Guard",
    shortLabel: "Cliff",
    description: "Slab protection once a verified tariff file is loaded.",
    icon: Shield,
    mobile: "tab",
  },
  {
    href: "/meter-readings",
    label: "Meter Readings",
    shortLabel: "Readings",
    description: "Manual checkpoints submitted by the household. Not a live feed.",
    icon: Gauge,
    mobile: "tab",
  },
  {
    href: "/action-plan",
    label: "Action Plan",
    shortLabel: "Plan",
    description: "Household actions. A saved plan is not available yet.",
    icon: ListChecks,
    mobile: "tab",
  },
  {
    href: "/bill-auditor",
    label: "Bill Auditor",
    shortLabel: "Auditor",
    description: "Bill comparison is not available yet. No bill is judged here.",
    icon: FileSearch,
    mobile: "more",
  },
  {
    href: "/history",
    label: "History",
    shortLabel: "History",
    description: "Earlier cycles will appear here once readings are stored.",
    icon: History,
    mobile: "more",
  },
  {
    href: "/settings",
    label: "Settings",
    shortLabel: "Settings",
    description: "Appearance stays on this device. Household settings are not saved yet.",
    icon: Settings,
    mobile: "more",
  },
];

export function isNavActive(pathname: string, href: NavHref): boolean {
  if (href === "/") {
    return pathname === "/";
  }

  return pathname === href || pathname.startsWith(`${href}/`);
}

export function navigationItem(href: NavHref): NavigationItem {
  const item = navigation.find((entry) => entry.href === href);
  if (!item) {
    throw new Error(`Missing navigation item for ${href}`);
  }
  return item;
}

export function currentNavigationItem(pathname: string): NavigationItem | null {
  return navigation.find((item) => isNavActive(pathname, item.href)) ?? null;
}
