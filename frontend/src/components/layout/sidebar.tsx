"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { isNavActive, navigation } from "@/lib/navigation";
import { cn } from "@/lib/cn";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r border-line bg-sidebar md:flex">
      <div className="border-b border-line px-3 py-4">
        <Link
          href="/"
          className="flex min-h-12 items-center gap-3 rounded-xl px-2"
        >
          <span
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-aqua font-display text-sm font-semibold text-ink"
            aria-hidden="true"
          >
            Bb
          </span>
          <span className="min-w-0">
            <span className="block font-display text-base font-semibold leading-tight">
              BijliBachat
            </span>
            <span lang="ur" dir="rtl" className="mt-1 block font-urdu text-sm leading-8 text-muted">
              بجلی بچت
            </span>
          </span>
        </Link>
      </div>

      <nav aria-label="Primary" className="flex-1 overflow-y-auto px-3 py-3">
        <ul className="flex flex-col gap-1">
          {navigation.map((item) => {
            const active = isNavActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-h-12 items-center gap-3 rounded-xl px-3 text-sm font-medium",
                    active
                      ? "bg-raised text-foreground shadow-[inset_3px_0_0_#42c8e8]"
                      : "text-muted hover:bg-raised/70 hover:text-foreground",
                  )}
                >
                  <Icon className="h-5 w-5 shrink-0" aria-hidden="true" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <p className="border-t border-line px-4 py-4 text-xs leading-5 text-muted">
        Overview uses sample data.
      </p>
    </aside>
  );
}
