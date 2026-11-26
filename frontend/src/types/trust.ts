export const dataTrustStatuses = [
  "verified",
  "calculated",
  "extracted",
  "estimated",
  "unavailable",
] as const;

export type DataTrustStatus = (typeof dataTrustStatuses)[number];

export const riskLevels = [
  "safe",
  "approaching",
  "high-risk",
  "needs-verification",
] as const;

export type RiskLevel = (typeof riskLevels)[number];
