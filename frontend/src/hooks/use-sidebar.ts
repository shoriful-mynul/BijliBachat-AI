"use client";

import { useSyncExternalStore } from "react";
import { SIDEBAR_STORAGE_KEY, type SidebarMode } from "@/lib/sidebar";

const sidebarChangeEvent = "bb-sidebar-change";

function subscribe(onStoreChange: () => void) {
  window.addEventListener(sidebarChangeEvent, onStoreChange);
  return () => window.removeEventListener(sidebarChangeEvent, onStoreChange);
}

function getSnapshot(): SidebarMode {
  return document.documentElement.dataset.sidebar === "collapsed" ? "collapsed" : "expanded";
}

function getServerSnapshot(): SidebarMode {
  return "expanded";
}

function applyMode(next: SidebarMode) {
  if (next === "collapsed") {
    document.documentElement.dataset.sidebar = "collapsed";
  } else {
    document.documentElement.removeAttribute("data-sidebar");
  }

  try {
    localStorage.setItem(SIDEBAR_STORAGE_KEY, next);
  } catch {
    // The choice still applies for this view when storage is blocked.
  }

  window.dispatchEvent(new Event(sidebarChangeEvent));
}

export function useSidebar() {
  const mode = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  return {
    mode,
    collapsed: mode === "collapsed",
    setMode: applyMode,
  };
}
