"use client";

import { useId, type InputHTMLAttributes } from "react";
import { AlertTriangle } from "lucide-react";
import { useI18n } from "@/components/i18n/language-provider";
import { cn } from "@/lib/cn";

type InputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "className"> & {
  label: string;
  hint?: string;
  error?: string;
  className?: string;
};

export function Input({
  label,
  hint,
  error,
  className,
  id,
  ...props
}: InputProps) {
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
      <input
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-required={props.required ? true : undefined}
        aria-describedby={describedBy}
        className="h-12 rounded-xl border border-line bg-background px-3 text-base text-foreground placeholder:text-muted disabled:cursor-not-allowed disabled:opacity-70 read-only:bg-raised"
        {...props}
      />
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
