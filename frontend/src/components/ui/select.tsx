"use client";

import { useId, type SelectHTMLAttributes } from "react";
import { AlertTriangle, ChevronDown } from "lucide-react";
import { useI18n } from "@/components/i18n/language-provider";
import { cn } from "@/lib/cn";

type SelectOption = {
  value: string;
  label: string;
};

type SelectProps = Omit<
  SelectHTMLAttributes<HTMLSelectElement>,
  "className" | "children"
> & {
  label: string;
  hint?: string;
  error?: string;
  options: readonly SelectOption[];
  className?: string;
};

export function Select({
  label,
  hint,
  error,
  options,
  className,
  id,
  ...props
}: SelectProps) {
  const { t } = useI18n();
  const generatedId = useId();
  const fieldId = id ?? generatedId;
  const hintId = hint ? `${fieldId}-hint` : undefined;
  const errorId = error ? `${fieldId}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  const requiredText = props.required ? ` (${t("common.required")})` : "";

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <label htmlFor={fieldId} className="text-sm font-medium">
        {label}
        {requiredText}
      </label>
      <div className="relative">
        <select
          id={fieldId}
          aria-invalid={error ? true : undefined}
          aria-required={props.required ? true : undefined}
          aria-describedby={describedBy}
          className="h-12 w-full appearance-none rounded-xl border border-line bg-background ps-3 pe-10 text-base text-foreground"
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute top-1/2 end-3 h-4 w-4 -translate-y-1/2 text-muted"
          aria-hidden="true"
        />
      </div>
      {hint ? (
        <p id={hintId} className="text-sm text-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} role="alert" className="flex items-start gap-2 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>{t("common.errorPrefix", { message: error })}</span>
        </p>
      ) : null}
    </div>
  );
}
