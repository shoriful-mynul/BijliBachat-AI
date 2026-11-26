"use client";

import Link from "next/link";
import { Settings } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import { useI18n } from "@/components/i18n/language-provider";
import { demoOverview } from "@/features/overview/demo-data";

type UserMenuProps = {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
};

export function UserMenu({ open, onOpen, onClose }: UserMenuProps) {
  const panelId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const settingsRef = useRef<HTMLAnchorElement>(null);
  const { t } = useI18n();
  const household = demoOverview.household;

  useEffect(() => {
    if (!open) {
      return;
    }

    settingsRef.current?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        buttonRef.current?.focus();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  const close = () => {
    onClose();
    buttonRef.current?.focus();
  };

  return (
    <div className="relative z-50">
      <button
        ref={buttonRef}
        type="button"
        className="flex h-12 min-w-12 items-center justify-center gap-2 rounded-xl px-2 hover:bg-raised"
        aria-expanded={open}
        aria-controls={panelId}
        aria-haspopup="menu"
        aria-label={t("shell.accountMenu")}
        title={t("shell.accountPanel")}
        onClick={() => (open ? close() : onOpen())}
      >
        <span
          className="grid h-8 w-8 place-items-center rounded-full bg-raised font-display text-xs font-semibold"
          aria-hidden="true"
        >
          {household.initials}
        </span>
        <span className="hidden text-start lg:block" aria-hidden="true">
          <span className="block text-sm font-medium leading-tight">
            <bdi>{household.fullName}</bdi>
          </span>
          <span className="block text-xs text-muted">{t("shell.sampleHousehold")}</span>
        </span>
      </button>
      {open ? (
        <div
          id={panelId}
          role="menu"
          aria-label={t("shell.accountPanel")}
          className="absolute end-0 z-50 mt-2 w-[min(18rem,calc(100vw-2rem))] rounded-2xl border border-line bg-card p-3 text-foreground"
        >
          <p className="px-2 text-sm font-semibold">
            <bdi>{household.fullName}</bdi>
          </p>
          <p className="px-2 text-xs text-muted">{t("shell.notSignedIn")}</p>
          <p className="mt-2 px-2 text-sm leading-6 text-muted">{t("shell.signInLater")}</p>
          <Link
            ref={settingsRef}
            href="/settings"
            role="menuitem"
            className="mt-2 flex min-h-12 items-center gap-3 rounded-xl px-2 text-sm font-medium hover:bg-raised"
            onClick={onClose}
          >
            <Settings className="h-5 w-5 shrink-0" aria-hidden="true" />
            {t("nav.settings.label")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
