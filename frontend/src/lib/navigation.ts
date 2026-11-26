import {
  FileSearch,
  Gauge,
  History,
  LayoutDashboard,
  ListChecks,
  TrendingUp,
  Settings,
  Shield,
  type LucideIcon,
} from "lucide-react";

export type NavHref =
  | "/dashboard"
  | "/prediction"
  | "/cliff-guard"
  | "/bill-auditor"
  | "/meter-readings"
  | "/action-plan"
  | "/history"
  | "/settings";

export type NavGroupId = "understand" | "prevent" | "optimize" | "measure";

type BaseNavigationItem = {
  href: NavHref;
  label: string;
  shortLabel: string;
  description: string;
  icon: LucideIcon;
  group: NavGroupId | "account";
  mobile: "tab" | "more";
  mobileOrder: number;
};

export type PlaceholderNavigationItem = BaseNavigationItem & {
  status: "placeholder";
  purpose: string;
  later: string;
};

export type NavigationItem =
  | (BaseNavigationItem & { status: "sample" | "settings" | "ready" })
  | PlaceholderNavigationItem;

export const navigationGroups: readonly { id: NavGroupId; label: string }[] = [
  { id: "understand", label: "Understand" },
  { id: "prevent", label: "Prevent" },
  { id: "optimize", label: "Optimize" },
  { id: "measure", label: "Measure" },
];

/**
 * Single route list for the shell. Desktop groups, the mobile tab bar,
 * and the More sheet all read this array.
 */
export const navigation: readonly NavigationItem[] = [
  {
    href: "/dashboard",
    label: "Overview",
    shortLabel: "Overview",
    description: "A sample look at one household cycle. The figures are labeled demo data.",
    icon: LayoutDashboard,
    group: "understand",
    mobile: "tab",
    mobileOrder: 1,
    status: "sample",
  },
  {
    href: "/prediction",
    label: "Forecast",
    shortLabel: "Forecast",
    description: "Estimated cycle use from your checkpoints, and a budget you enter yourself.",
    icon: TrendingUp,
    group: "understand",
    mobile: "more",
    mobileOrder: 0,
    status: "ready",
  },
  {
    href: "/cliff-guard",
    label: "Cliff Guard",
    shortLabel: "Cliff",
    description: "Checkpoints and the distance to a verified tariff threshold, when one exists.",
    icon: Shield,
    group: "prevent",
    mobile: "tab",
    mobileOrder: 2,
    status: "ready",
  },
  {
    href: "/bill-auditor",
    label: "Bill Auditor",
    shortLabel: "Auditor",
    description:
      "Upload a bill, review what was read, and compare confirmed amounts with the tariff engine.",
    icon: FileSearch,
    group: "prevent",
    mobile: "more",
    mobileOrder: 1,
    status: "ready",
  },
  {
    href: "/action-plan",
    label: "Action Plan",
    shortLabel: "Plan",
    description: "Enter appliance use, try a different schedule, and see the kWh difference.",
    icon: ListChecks,
    group: "optimize",
    mobile: "tab",
    mobileOrder: 4,
    status: "ready",
  },
  {
    href: "/meter-readings",
    label: "Meter Readings",
    shortLabel: "Readings",
    description: "Manual and photo checkpoints kept on this device. This is not a live meter.",
    icon: Gauge,
    group: "measure",
    mobile: "tab",
    mobileOrder: 3,
    status: "ready",
  },
  {
    href: "/history",
    label: "Consumption History",
    shortLabel: "History",
    description: "Month-by-month comparison later. Nothing is stored yet.",
    icon: History,
    group: "measure",
    mobile: "more",
    mobileOrder: 2,
    status: "placeholder",
    purpose: "You will be able to compare months and see actual use next to an estimate.",
    later: "Nothing is stored yet, so there is no history to show.",
  },
  {
    href: "/settings",
    label: "Settings",
    shortLabel: "Settings",
    description: "Theme on this device. Other choices are not saved yet.",
    icon: Settings,
    group: "account",
    mobile: "more",
    mobileOrder: 3,
    status: "settings",
  },
];

export function isNavActive(pathname: string, href: NavHref): boolean {
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

export function navigationInGroup(group: NavGroupId): NavigationItem[] {
  return navigation.filter((item) => item.group === group);
}

export function mobileTabs(): NavigationItem[] {
  return navigation
    .filter((item) => item.mobile === "tab")
    .slice()
    .sort((left, right) => left.mobileOrder - right.mobileOrder);
}

export function mobileMore(): NavigationItem[] {
  return navigation
    .filter((item) => item.mobile === "more")
    .slice()
    .sort((left, right) => left.mobileOrder - right.mobileOrder);
}
