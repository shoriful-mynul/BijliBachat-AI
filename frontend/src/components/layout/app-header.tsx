"use client";

import { usePathname } from "next/navigation";
import { useCallback, useState } from "react";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { NotificationButton } from "@/components/layout/notification-button";
import { PageHeader } from "@/components/layout/page-header";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { UserMenu } from "@/components/layout/user-menu";
import { currentNavigationItem } from "@/lib/navigation";

type HeaderMenu = "notifications" | "account";

export function AppHeader() {
  const pathname = usePathname();
  const current = currentNavigationItem(pathname);
  const title = current?.label ?? "Page not found";
  const description = current?.description ?? "This address is not part of BijliBachat.";
  const [menu, setMenu] = useState<HeaderMenu | null>(null);
  const [openPath, setOpenPath] = useState<string | null>(null);
  const openMenu = openPath === pathname ? menu : null;

  const closeMenus = useCallback(() => {
    setMenu(null);
    setOpenPath(null);
  }, []);

  const open = useCallback(
    (next: HeaderMenu) => {
      setMenu(next);
      setOpenPath(pathname);
    },
    [pathname],
  );

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-background pt-[env(safe-area-inset-top)]">
      <div className="flex items-center gap-2 px-4 py-2 md:px-8 md:py-3">
        <div className="min-w-0 flex-1">
          <Breadcrumbs current={current} />
          <PageHeader title={title} description={description} />
        </div>
        <div className="flex shrink-0 items-center">
          <ThemeToggle />
          <NotificationButton
            open={openMenu === "notifications"}
            onOpen={() => open("notifications")}
            onClose={closeMenus}
          />
          <UserMenu
            open={openMenu === "account"}
            onOpen={() => open("account")}
            onClose={closeMenus}
          />
        </div>
      </div>
      {openMenu ? (
        <button
          type="button"
          className="fixed inset-0 z-40 cursor-default"
          aria-label="Close menu"
          onClick={closeMenus}
        />
      ) : null}
    </header>
  );
}
