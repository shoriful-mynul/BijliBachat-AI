"use client";

import { Bell } from "lucide-react";
import { useEffect, useId, useRef } from "react";

type NotificationButtonProps = {
  open: boolean;
  onOpen: () => void;
  onClose: () => void;
};

export function NotificationButton({ open, onOpen, onClose }: NotificationButtonProps) {
  const panelId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    panelRef.current?.focus();

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
        className="grid h-12 w-12 place-items-center rounded-xl hover:bg-raised"
        aria-expanded={open}
        aria-controls={panelId}
        aria-haspopup="dialog"
        aria-label="Notifications"
        title="Notifications"
        onClick={() => (open ? close() : onOpen())}
      >
        <Bell className="h-5 w-5" aria-hidden="true" />
      </button>
      {open ? (
        <div
          ref={panelRef}
          id={panelId}
          role="dialog"
          tabIndex={-1}
          aria-label="Notifications"
          className="absolute right-0 z-50 mt-2 w-[min(18rem,calc(100vw-2rem))] rounded-2xl border border-line bg-card p-4 text-foreground"
        >
          <p className="text-sm font-semibold">No notifications</p>
          <p className="mt-1 text-sm leading-6 text-muted">
            Delivery is not part of this version. Nothing is waiting, and no alert is being sent.
          </p>
          <button
            type="button"
            className="mt-3 flex min-h-12 w-full items-center justify-center rounded-xl bg-raised text-sm font-semibold hover:bg-background"
            onClick={close}
          >
            Close
          </button>
        </div>
      ) : null}
    </div>
  );
}
