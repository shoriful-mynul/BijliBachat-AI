"use client";

import { useEffect, useState } from "react";
import { DataTrustChip } from "@/components/ui/data-trust-chip";
import { getApiBaseUrl, isHealthResponse } from "@/lib/health";
import type { HealthResponse } from "@/types/health";

type StatusState =
  | { kind: "loading" }
  | { kind: "unconfigured" }
  | { kind: "unreachable" }
  | { kind: "unexpected" }
  | { kind: "ok"; health: HealthResponse };

const checkLabels: Record<HealthResponse["checks"][number]["name"], string> = {
  process: "API process",
  firebase: "Firebase",
  gemini: "Gemini",
  tariff_configuration: "Tariff file",
};

export function ServiceStatus() {
  const [state, setState] = useState<StatusState>(() =>
    getApiBaseUrl() ? { kind: "loading" } : { kind: "unconfigured" },
  );

  useEffect(() => {
    const baseUrl = getApiBaseUrl();
    if (!baseUrl) {
      return;
    }

    const controller = new AbortController();

    fetch(`${baseUrl}/api/health`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          setState({ kind: "unexpected" });
          return;
        }

        const body: unknown = await response.json();
        if (!isHealthResponse(body)) {
          setState({ kind: "unexpected" });
          return;
        }

        setState({ kind: "ok", health: body });
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setState({ kind: "unreachable" });
      });

    return () => controller.abort();
  }, []);

  return (
    <footer className="border-t border-line pt-4 text-sm">
      <h2 className="font-display text-sm font-semibold">Service status</h2>
      {state.kind === "loading" ? (
        <p className="mt-2 text-muted" role="status">
          Checking the API…
        </p>
      ) : null}
      {state.kind === "unconfigured" ? (
        <StatusLine label="API address is not configured in this build." />
      ) : null}
      {state.kind === "unreachable" ? (
        <StatusLine label="The API could not be reached." />
      ) : null}
      {state.kind === "unexpected" ? (
        <StatusLine label="The API did not return a health payload." />
      ) : null}
      {state.kind === "ok" ? (
        <div className="mt-2">
          <p className="leading-6 text-muted">{state.health.detail}</p>
          <ul className="mt-3 flex flex-col gap-2">
            {state.health.checks.map((check) => (
              <li key={check.name} className="flex flex-wrap items-center gap-2">
                <span className="min-w-28 text-foreground">{checkLabels[check.name]}</span>
                {check.state === "ok" ? (
                  <span className="font-medium">Running</span>
                ) : (
                  <DataTrustChip status="unavailable" />
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </footer>
  );
}

function StatusLine({ label }: { label: string }) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      <DataTrustChip status="unavailable" />
      <p className="text-muted">{label}</p>
    </div>
  );
}
