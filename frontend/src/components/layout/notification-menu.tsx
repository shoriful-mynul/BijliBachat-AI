"use client";

import { Bell } from "lucide-react";
import { useEffect, useId, useState } from "react";

export function NotificationMenu() {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  useEffect(() => {
    if (!open) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  return (
    <div className="relative">
      <button
        type="button"
        className="grid h-12 w-12 place-items-center rounded-xl hover:bg-raised"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label="Notifications"
        onClick={() => setOpen((value) => !value)}
      >
        <Bell className="h-5 w-5" aria-hidden="true" />
      </button>
      {open ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 cursor-default"
            aria-label="Close notifications"
            onClick={() => setOpen(false)}
          />
          <div
            id={panelId}
            role="region"
            aria-label="Notifications"
            className="absolute right-0 z-50 mt-2 w-72 rounded-2xl border border-line bg-card p-4 text-foreground"
          >
            <p className="text-sm font-semibold">No notifications</p>
            <p className="mt-1 text-sm leading-6 text-muted">
              Delivery is not part of this version. Nothing is waiting.
            </p>
          </div>
        </>
      ) : null}
    </div>
  );
}
