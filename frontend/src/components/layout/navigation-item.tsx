"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type FocusEvent, type MouseEvent } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "@/components/i18n/language-provider";
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
  const { t, direction } = useI18n();
  const label = t(item.labelKey);
  const shortLabel = t(item.shortKey);
  const description = t(item.descriptionKey);
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
        aria-label={variant === "row" ? undefined : label}
        title={variant === "sidebar" && tooltip ? label : undefined}
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
              ? "nav-rail bg-raised text-foreground"
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
          <span className="sidebar-expanded-only text-start leading-snug" aria-hidden="true">
            {label}
          </span>
        ) : null}
        {variant === "tab" ? <span aria-hidden="true">{shortLabel}</span> : null}
        {variant === "row" ? (
          <span className="min-w-0">
            <span className="block">{label}</span>
            <span className="block text-xs leading-5 font-normal text-muted">{description}</span>
          </span>
        ) : null}
      </Link>
      {tooltip && tip ? <CollapsedTooltip label={label} anchor={anchor} rtl={direction === "rtl"} /> : null}
    </>
  );
}

function CollapsedTooltip({
  label,
  anchor,
  rtl,
}: {
  label: string;
  anchor: HTMLElement | null;
  rtl: boolean;
}) {
  if (!anchor) {
    return null;
  }

  const rect = anchor.getBoundingClientRect();
  const top = rect.top + rect.height / 2;

  return createPortal(
    <span
      aria-hidden="true"
      style={
        rtl
          ? { top, right: window.innerWidth - rect.left + 8 }
          : { top, left: rect.right + 8 }
      }
      className="pointer-events-none fixed z-50 -translate-y-1/2 rounded-xl border border-line bg-card px-2.5 py-1.5 text-sm text-foreground"
    >
      {label}
    </span>,
    document.body,
  );
}
