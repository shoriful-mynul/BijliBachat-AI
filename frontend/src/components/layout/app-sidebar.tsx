"use client";

import Link from "next/link";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { NavigationItem } from "@/components/layout/navigation-item";
import { useSidebar } from "@/hooks/use-sidebar";
import { demoOverview } from "@/features/overview/demo-data";
import {
  navigationGroups,
  navigationInGroup,
  navigationItem,
} from "@/lib/navigation";

export function AppSidebar() {
  const { collapsed, setMode } = useSidebar();
  const settings = navigationItem("/settings");
  const household = demoOverview.household;

  return (
    <aside className="app-sidebar sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-line bg-sidebar md:flex">
      <div className="border-b border-line px-3 py-4">
        <Link
          href="/dashboard"
          aria-label="BijliBachat, home"
          title={collapsed ? "BijliBachat" : undefined}
          className="nav-link flex min-h-12 items-center gap-3 rounded-xl px-2"
        >
          <span
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-aqua font-display text-sm font-semibold text-ink"
            aria-hidden="true"
          >
            Bb
          </span>
          <span className="sidebar-expanded-only min-w-0">
            <span className="block font-display text-base font-semibold leading-tight">
              BijliBachat
            </span>
            <span
              lang="ur"
              dir="rtl"
              className="mt-1 inline-block font-urdu text-sm leading-8 text-muted"
            >
              بجلی بچت
            </span>
          </span>
        </Link>
      </div>

      <nav id="primary-nav" aria-label="Primary" className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        <div className="nav-groups flex flex-col gap-4">
          {navigationGroups.map((group) => (
            <div key={group.id} className="nav-group">
              <p className="sidebar-expanded-only px-3 pb-1 text-xs font-medium text-muted" aria-hidden="true">
                {group.label}
              </p>
              <ul aria-label={group.label} className="flex flex-col gap-1">
                {navigationInGroup(group.id).map((item) => (
                  <li key={item.href}>
                    <NavigationItem item={item} variant="sidebar" tooltip={collapsed} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </nav>

      <div className="border-t border-line p-3">
        <div className="sidebar-identity flex min-h-12 items-center gap-3 px-2">
          <span className="sr-only">Sample household, {household.fullName}. Not signed in.</span>
          <span
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-raised font-display text-xs font-semibold"
            aria-hidden="true"
          >
            {household.initials}
          </span>
          <span className="sidebar-expanded-only min-w-0" aria-hidden="true">
            <span className="block truncate text-sm font-medium leading-tight">{household.fullName}</span>
            <span className="block text-xs text-muted">Sample household</span>
          </span>
        </div>
        <NavigationItem item={settings} variant="sidebar" tooltip={collapsed} />
        <button
          type="button"
          className="nav-link relative mt-1 flex min-h-12 w-full items-center gap-3 rounded-xl px-3 text-sm font-medium text-muted hover:bg-raised/70 hover:text-foreground"
          aria-pressed={collapsed}
          aria-controls="primary-nav"
          title="Collapse or expand sidebar"
          onClick={() => setMode(collapsed ? "expanded" : "collapsed")}
        >
          <PanelLeftClose className="sidebar-expanded-only h-5 w-5 shrink-0" aria-hidden="true" />
          <PanelLeftOpen className="sidebar-collapsed-only h-5 w-5 shrink-0" aria-hidden="true" />
          <span className="sidebar-expanded-only">Collapse sidebar</span>
          <span className="sidebar-collapsed-name">Expand sidebar</span>
        </button>
        <p className="sidebar-expanded-only px-3 pt-2 text-xs leading-5 text-muted">
          Overview uses sample data.
        </p>
      </div>
    </aside>
  );
}
