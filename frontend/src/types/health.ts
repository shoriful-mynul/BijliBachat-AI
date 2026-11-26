export const healthCheckNames = [
  "process",
  "firebase",
  "gemini",
  "tariff_configuration",
] as const;

export type HealthCheckName = (typeof healthCheckNames)[number];

export type HealthCheckState = "ok" | "not_configured";

export type HealthCheck = {
  name: HealthCheckName;
  state: HealthCheckState;
  detail: string;
};

export type HealthResponse = {
  status: "ok";
  service: string;
  version: string;
  environment: "development" | "test" | "production";
  detail: string;
  checked_at: string;
  checks: HealthCheck[];
};
