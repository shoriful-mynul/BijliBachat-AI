"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NotificationMenu } from "@/components/layout/notification-menu";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { currentNavigationItem } from "@/lib/navigation";
import { demoOverview } from "@/features/overview/demo-data";

export function Topbar() {
  const pathname = usePathname();
  const current = currentNavigationItem(pathname);
  const title = current?.label ?? "Page not found";
  const description =
    current?.description ?? "This address is not part of BijliBachat.";

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-background">
      <div className="flex items-start gap-2 px-4 py-3 md:px-8">
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-lg font-semibold leading-snug md:text-xl">
            {title}
          </h1>
          <p className="mt-0.5 text-sm leading-5 text-muted">{description}</p>
        </div>
        <div className="flex shrink-0 items-center">
          <ThemeToggle />
          <NotificationMenu />
          <Link
            href="/settings"
            className="flex h-12 min-w-12 items-center justify-center gap-2 rounded-xl px-2 hover:bg-raised"
          >
            <span
              className="grid h-8 w-8 place-items-center rounded-full bg-raised font-display text-xs font-semibold"
              aria-hidden="true"
            >
              {demoOverview.household.initials}
            </span>
            <span className="hidden text-left lg:block">
              <span className="block text-sm font-medium leading-tight">
                {demoOverview.household.fullName}
              </span>
              <span className="block text-xs text-muted">Demo profile</span>
            </span>
            <span className="sr-only lg:hidden">Sample household settings</span>
          </Link>
        </div>
      </div>
    </header>
  );
}
