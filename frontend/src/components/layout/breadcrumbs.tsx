import Link from "next/link";
import type { NavigationItem } from "@/lib/navigation";

export function Breadcrumbs({ current }: { current: NavigationItem | null }) {
  if (!current || current.href === "/dashboard") {
    return null;
  }

  return (
    <nav aria-label="Breadcrumb" className="mb-1 hidden md:block">
      <ol className="flex items-center gap-2 text-xs text-muted">
        <li>
          <Link href="/dashboard" className="rounded-md hover:text-foreground">
            Home
          </Link>
        </li>
        <li aria-hidden="true">/</li>
        <li aria-current="page" className="text-foreground">
          {current.label}
        </li>
      </ol>
    </nav>
  );
}
