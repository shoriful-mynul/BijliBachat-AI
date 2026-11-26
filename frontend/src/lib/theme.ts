export const THEME_STORAGE_KEY = "bb-theme";

export const themes = ["dark", "light"] as const;

export type Theme = (typeof themes)[number];

export function isTheme(value: string | null | undefined): value is Theme {
  return value === "dark" || value === "light";
}

/**
 * Runs in the document head before first paint.
 * Only the two known theme names are accepted.
 */
export const themeInitScript = `(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});if(t==="light"||t==="dark")document.documentElement.setAttribute("data-theme",t);}catch(e){}})();`;
