import {
  healthCheckNames,
  type HealthCheck,
  type HealthResponse,
} from "@/types/health";

const environments = new Set(["development", "test", "production"]);

function isCheck(value: unknown): value is HealthCheck {
  if (!value || typeof value !== "object") {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    typeof record.name === "string" &&
    healthCheckNames.includes(record.name as HealthCheck["name"]) &&
    (record.state === "ok" || record.state === "not_configured") &&
    typeof record.detail === "string"
  );
}

export function isHealthResponse(value: unknown): value is HealthResponse {
  if (!value || typeof value !== "object") {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    record.status === "ok" &&
    typeof record.service === "string" &&
    typeof record.version === "string" &&
    typeof record.environment === "string" &&
    environments.has(record.environment) &&
    typeof record.detail === "string" &&
    typeof record.checked_at === "string" &&
    Array.isArray(record.checks) &&
    record.checks.every(isCheck)
  );
}

export function getApiBaseUrl(): string | null {
  const value = process.env.NEXT_PUBLIC_API_URL;
  if (!value) {
    return null;
  }

  const trimmed = value.trim().replace(/\/$/, "");
  if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
    return null;
  }

  return trimmed;
}
