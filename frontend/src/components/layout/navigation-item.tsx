"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type FocusEvent, type MouseEvent } from "react";
import { createPortal } from "react-dom";
import { isNavActive, type NavigationItem as NavigationItemData } from "@/lib/navigation";
import { cn } from "@/lib/cn";

type NavigationItemProps = {
  item: NavigationItemData;
  variant: "sidebar" | "tab" | "row";
  tooltip?: boolean;
  onNavigate?: () => void;
};

export function NavigationItem({ item, variant, tooltip = false, onNavigate }: NavigationItemProps) {
  const pathname = usePathname();
  const active = isNavActive(pathname, item.href);
  const Icon = item.icon;
  const [tip, setTip] = useState(false);
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  const showTip = (event: MouseEvent<HTMLAnchorElement> | FocusEvent<HTMLAnchorElement>) => {
    setAnchor(event.currentTarget);
    setTip(true);
  };

  const hideTip = () => setTip(false);

  return (
    <>
      <Link
        href={item.href}
        aria-current={active ? "page" : undefined}
        aria-label={variant === "row" ? undefined : item.label}
        title={variant === "sidebar" && tooltip ? item.label : undefined}
        onClick={onNavigate}
        onMouseEnter={tooltip ? showTip : undefined}
        onMouseLeave={tooltip ? hideTip : undefined}
        onFocus={tooltip ? showTip : undefined}
        onBlur={tooltip ? hideTip : undefined}
        className={cn(
          "rounded-xl font-medium",
          variant === "sidebar" &&
            "nav-link flex min-h-12 items-center gap-3 px-3 text-sm",
          variant === "tab" &&
            "flex min-h-16 w-full flex-col items-center justify-center gap-1 px-1 text-xs",
          variant === "row" && "flex min-h-12 items-center gap-3 px-2 text-sm",
          variant === "sidebar" &&
            (active
              ? "bg-raised text-foreground shadow-[inset_3px_0_0_#42c8e8]"
              : "text-muted hover:bg-raised/70 hover:text-foreground"),
          variant === "tab" &&
            (active
              ? "bg-raised font-semibold text-foreground shadow-[inset_0_2px_0_#42c8e8]"
              : "text-muted"),
          variant === "row" &&
            (active ? "bg-raised text-foreground" : "text-foreground hover:bg-raised"),
        )}
      >
        <Icon
          className={cn("h-5 w-5 shrink-0", variant === "tab" && active && "text-aqua")}
          aria-hidden="true"
        />
        {variant === "sidebar" ? (
          <span className="sidebar-expanded-only text-left leading-snug" aria-hidden="true">
            {item.label}
          </span>
        ) : null}
        {variant === "tab" ? <span aria-hidden="true">{item.shortLabel}</span> : null}
        {variant === "row" ? (
          <span className="min-w-0">
            <span className="block">{item.label}</span>
            <span className="block text-xs leading-5 font-normal text-muted">{item.description}</span>
          </span>
        ) : null}
      </Link>
      {tooltip && tip ? <CollapsedTooltip label={item.label} anchor={anchor} /> : null}
    </>
  );
}

function CollapsedTooltip({ label, anchor }: { label: string; anchor: HTMLElement | null }) {
  if (!anchor) {
    return null;
  }

  const rect = anchor.getBoundingClientRect();

  return createPortal(
    <span
      aria-hidden="true"
      style={{ top: rect.top + rect.height / 2, left: rect.right + 8 }}
      className="pointer-events-none fixed z-50 -translate-y-1/2 rounded-xl border border-line bg-card px-2.5 py-1.5 text-sm text-foreground"
    >
      {label}
    </span>,
    document.body,
  );
}
