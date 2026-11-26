"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/use-theme";

export function ThemeToggle() {
  const { setTheme } = useTheme();

  return (
    <button
      type="button"
      className="grid h-12 w-12 place-items-center rounded-xl hover:bg-raised"
      aria-label="Toggle color theme"
      onClick={() => {
        const current =
          document.documentElement.dataset.theme === "light" ? "light" : "dark";
        setTheme(current === "dark" ? "light" : "dark");
      }}
    >
      <Sun className="icon-when-dark h-5 w-5" aria-hidden="true" />
      <Moon className="icon-when-light h-5 w-5" aria-hidden="true" />
    </button>
  );
}
