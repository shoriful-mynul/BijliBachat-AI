export const SIDEBAR_STORAGE_KEY = "bb-sidebar";

export const sidebarModes = ["expanded", "collapsed"] as const;

export type SidebarMode = (typeof sidebarModes)[number];

export function isSidebarMode(value: string | null | undefined): value is SidebarMode {
  return value === "expanded" || value === "collapsed";
}

/**
 * Runs in the document head before first paint.
 * Only an explicit collapsed choice narrows the sidebar.
 */
export const sidebarInitScript = `(function(){try{var s=localStorage.getItem(${JSON.stringify(SIDEBAR_STORAGE_KEY)});if(s==="collapsed")document.documentElement.setAttribute("data-sidebar","collapsed");}catch(e){}})();`;
