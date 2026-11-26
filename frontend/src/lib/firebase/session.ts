/** Sign-in results that the screen can show. A missing configuration is never a success. */

export type AuthFailure = "invalid" | "weak" | "exists" | "unavailable" | "rejected";

export type AuthFormResult = { ok: true } | { ok: false; reason: AuthFailure };

export type SessionPhase = "loading" | "signed-out" | "signed-in" | "rejected";

export type SessionView =
  | { mode: "local" }
  | { mode: "cloud"; phase: "loading" | "signed-out" | "rejected" }
  | { mode: "cloud"; phase: "signed-in"; email: string };

export function mapAuthError(code: string): AuthFailure {
  if (code === "auth/weak-password") {
    return "weak";
  }
  if (code === "auth/email-already-in-use") {
    return "exists";
  }
  if (
    code === "auth/invalid-credential" ||
    code === "auth/invalid-email" ||
    code === "auth/wrong-password" ||
    code === "auth/user-not-found" ||
    code === "auth/user-disabled"
  ) {
    return "invalid";
  }
  if (code === "auth/network-request-failed" || code === "auth/too-many-requests") {
    return "unavailable";
  }
  return "rejected";
}

export function signInOutcome(configured: boolean, errorCode: string | null): AuthFormResult {
  if (!configured) {
    return { ok: false, reason: "unavailable" };
  }
  if (!errorCode) {
    return { ok: true };
  }
  return { ok: false, reason: mapAuthError(errorCode) };
}

export function sessionView(
  configured: boolean,
  phase: SessionPhase,
  email: string | null,
): SessionView {
  if (!configured) {
    return { mode: "local" };
  }
  if (phase === "signed-in" && email) {
    return { mode: "cloud", phase: "signed-in", email };
  }
  if (phase === "loading") {
    return { mode: "cloud", phase: "loading" };
  }
  if (phase === "rejected") {
    return { mode: "cloud", phase: "rejected" };
  }
  return { mode: "cloud", phase: "signed-out" };
}
