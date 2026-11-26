"use client";

import Link from "next/link";
import { Settings } from "lucide-react";
import { useEffect, useId, useRef } from "react";
import { useAuth } from "@/components/auth/auth-provider";
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
  const auth = useAuth();
  const household = demoOverview.household;
  const view = auth.view;
  let label: string = household.fullName;
  let initials: string = household.initials;
  let detail = view.mode === "local" ? t("shell.localAccount") : t("shell.cloudSignedOut");
  const signedIn = view.mode === "cloud" && view.phase === "signed-in";
  if (signedIn) {
    label = view.email;
    initials = view.email.slice(0, 1).toUpperCase();
    detail = t("shell.signedInAs", { email: view.email });
  }

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
          {initials}
        </span>
        <span className="hidden text-start lg:block" aria-hidden="true">
          <span className="block max-w-40 truncate text-sm font-medium leading-tight">
            <bdi>{label}</bdi>
          </span>
          <span className="block text-xs text-muted">
            {signedIn ? t("shell.sampleNote") : t("shell.sampleHousehold")}
          </span>
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
            <bdi>{label}</bdi>
          </p>
          <p className="mt-2 px-2 text-sm leading-6 text-muted">{detail}</p>
          {signedIn ? (
            <button
              type="button"
              role="menuitem"
              className="mt-2 flex min-h-12 w-full items-center rounded-xl px-2 text-start text-sm font-medium hover:bg-raised"
              onClick={() => {
                void auth.signOut();
                onClose();
              }}
            >
              {t("shell.signOut")}
            </button>
          ) : null}
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
