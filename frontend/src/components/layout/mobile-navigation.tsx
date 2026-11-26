"use client";

import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { NavigationItem } from "@/components/layout/navigation-item";
import { isNavActive, mobileMore, mobileTabs } from "@/lib/navigation";
import { cn } from "@/lib/cn";

export function MobileNavigation() {
  const pathname = usePathname();
  const [openPath, setOpenPath] = useState<string | null>(null);
  const open = openPath === pathname;
  const tabs = mobileTabs();
  const moreItems = mobileMore();
  const moreActive = moreItems.some((item) => isNavActive(pathname, item.href));
  const closeSheet = useCallback(() => setOpenPath(null), []);

  return (
    <>
      <nav
        aria-label="Primary"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-sidebar md:hidden"
      >
        <ul className="grid grid-cols-5 pb-[env(safe-area-inset-bottom)]">
          {tabs.map((item) => (
            <li key={item.href}>
              <NavigationItem item={item} variant="tab" />
            </li>
          ))}
          <li>
            <button
              type="button"
              className={cn(
                "flex min-h-16 w-full flex-col items-center justify-center gap-1 px-1 text-xs",
                moreActive || open
                  ? "bg-raised font-semibold text-foreground shadow-[inset_0_2px_0_#42c8e8]"
                  : "font-medium text-muted",
              )}
              aria-haspopup="dialog"
              aria-expanded={open}
              aria-label="More sections"
              onClick={() => setOpenPath(open ? null : pathname)}
            >
              <Menu
                className={cn("h-5 w-5", (moreActive || open) && "text-aqua")}
                aria-hidden="true"
              />
              <span aria-hidden="true">More</span>
            </button>
          </li>
        </ul>
      </nav>
      {open ? <MoreSheet onClose={closeSheet} /> : null}
    </>
  );
}

function MoreSheet({ onClose }: { onClose: () => void }) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  const moreItems = mobileMore();

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 md:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-ink/60"
        aria-label="Close menu"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="absolute inset-x-0 bottom-0 rounded-t-2xl border border-line bg-sidebar px-4 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))] text-foreground"
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-line" aria-hidden="true" />
        <div className="mb-2 flex items-center justify-between gap-3">
          <h2 id={titleId} className="font-display text-base font-semibold">
            More
          </h2>
          <button
            ref={closeRef}
            type="button"
            className="grid h-12 w-12 place-items-center rounded-xl hover:bg-raised"
            onClick={onClose}
            aria-label="Close menu"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <ul className="flex flex-col gap-1">
          {moreItems.map((item) => (
            <li key={item.href}>
              <NavigationItem item={item} variant="row" onNavigate={onClose} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
