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
import type { MessageKey } from "@/lib/i18n/messages";

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
  labelKey: MessageKey;
  shortKey: MessageKey;
  descriptionKey: MessageKey;
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

export const navigationGroups: readonly { id: NavGroupId; labelKey: MessageKey }[] = [
  { id: "understand", labelKey: "nav.group.understand" },
  { id: "prevent", labelKey: "nav.group.prevent" },
  { id: "optimize", labelKey: "nav.group.optimize" },
  { id: "measure", labelKey: "nav.group.measure" },
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
    labelKey: "nav.overview.label",
    shortKey: "nav.overview.short",
    descriptionKey: "nav.overview.description",
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
    labelKey: "nav.forecast.label",
    shortKey: "nav.forecast.short",
    descriptionKey: "nav.forecast.description",
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
    labelKey: "nav.cliff.label",
    shortKey: "nav.cliff.short",
    descriptionKey: "nav.cliff.description",
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
    labelKey: "nav.bill.label",
    shortKey: "nav.bill.short",
    descriptionKey: "nav.bill.description",
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
    labelKey: "nav.plan.label",
    shortKey: "nav.plan.short",
    descriptionKey: "nav.plan.description",
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
    labelKey: "nav.meter.label",
    shortKey: "nav.meter.short",
    descriptionKey: "nav.meter.description",
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
    description: "Measured cycles from confirmed checkpoints, compared with a saved forecast.",
    labelKey: "nav.history.label",
    shortKey: "nav.history.short",
    descriptionKey: "nav.history.description",
    icon: History,
    group: "measure",
    mobile: "more",
    mobileOrder: 2,
    status: "ready",
  },
  {
    href: "/settings",
    label: "Settings",
    shortLabel: "Settings",
    description: "Language and theme on this device. Other choices are not saved yet.",
    labelKey: "nav.settings.label",
    shortKey: "nav.settings.short",
    descriptionKey: "nav.settings.description",
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
