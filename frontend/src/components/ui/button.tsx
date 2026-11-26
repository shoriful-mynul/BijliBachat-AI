import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<Variant, string> = {
  primary: "bg-aqua text-ink hover:brightness-[0.97]",
  secondary: "border border-line bg-raised text-foreground hover:bg-card",
  ghost: "bg-transparent text-foreground hover:bg-raised",
  danger:
    "danger-rail border border-line bg-transparent text-foreground hover:bg-raised",
};

const base =
  "inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60";

type CommonProps = {
  variant?: Variant;
  className?: string;
  children: ReactNode;
};

type ButtonAsButton = CommonProps &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className" | "children"> & {
    href?: undefined;
  };

type ButtonAsLink = CommonProps & {
  href: string;
};

type ButtonProps = ButtonAsButton | ButtonAsLink;

function isLink(props: ButtonProps): props is ButtonAsLink {
  return typeof props.href === "string";
}

export function Button(props: ButtonProps) {
  if (isLink(props)) {
    const { variant = "primary", className, children, href } = props;
    return (
      <Link href={href} className={cn(base, variants[variant], className)}>
        {children}
      </Link>
    );
  }

  const { variant = "primary", className, children, type, ...rest } = props;
  return (
    <button
      type={type ?? "button"}
      className={cn(base, variants[variant], className)}
      {...rest}
    >
      {children}
    </button>
  );
}
