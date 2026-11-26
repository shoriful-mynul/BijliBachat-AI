"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { useI18n } from "@/components/i18n/language-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { SectionHeader } from "@/components/ui/section-header";
import { accountRequest } from "@/lib/account/api";
import { clearDeviceRecords, recordsFromLocal, type CopyPlan } from "@/lib/account/local-copy";
import type { AuthFailure } from "@/lib/firebase/session";
import { getApiBaseUrl } from "@/lib/health";
import type { MessageKey } from "@/lib/i18n/messages";

const failureKey: Record<AuthFailure, MessageKey> = {
  invalid: "account.invalid",
  weak: "account.weak",
  exists: "account.exists",
  unavailable: "account.unavailable",
  rejected: "account.rejected",
};

const collectionKey: Record<string, MessageKey> = {
  meter_checkpoints: "account.meters",
  appliances: "account.appliances",
  history_cycles: "account.cycles",
  forecast_snapshots: "account.snapshots",
  history_baselines: "account.baselines",
};

export function AccountSection() {
  const { t } = useI18n();
  const auth = useAuth();
  const apiBase = getApiBaseUrl();
  const view = auth.view;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [providerCode, setProviderCode] = useState("");
  const [region, setRegion] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [includeLogin, setIncludeLogin] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const [plan, setPlan] = useState<CopyPlan | null>(null);

  useEffect(() => {
    queueMicrotask(() => setPlan(recordsFromLocal(window.localStorage)));
  }, [notice]);

  async function submit(action: "sign-in" | "register") {
    setBusy(true);
    setNotice(null);
    const result =
      action === "register" ? await auth.register(email.trim(), password) : await auth.signIn(email.trim(), password);
    setPassword("");
    setBusy(false);
    if (!result.ok) {
      setNotice(t(failureKey[result.reason]));
    }
  }

  async function copyRecords() {
    if (!apiBase || view.mode !== "cloud" || view.phase !== "signed-in" || !plan) {
      setNotice(t("account.copyNeedSignIn"));
      return;
    }
    setBusy(true);
    setNotice(null);
    const token = await auth.getToken();
    const response = await accountRequest(`${apiBase}/api/account/import`, token, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(plan.payload),
    });
    setBusy(false);
    if (!response.ok || !response.body || typeof response.body !== "object") {
      setNotice(t("account.copyFailed"));
      return;
    }
    const results = (response.body as { results?: { status?: string }[] }).results ?? [];
    const created = results.filter((item) => item.status === "created").length;
    const present = results.filter((item) => item.status === "already_present").length;
    const rejected = results.filter((item) => item.status === "rejected").length + plan.rejected.length;
    setNotice(t("account.copyResult", { created, present, rejected }));
  }

  async function saveHousehold() {
    if (!apiBase || view.mode !== "cloud" || view.phase !== "signed-in") {
      setNotice(t("account.notSaved"));
      return;
    }
    const existing = window.localStorage.getItem("bijlibachat.meter-household.v1");
    const id = existing ?? window.crypto.randomUUID();
    const now = new Date().toISOString();
    setBusy(true);
    const token = await auth.getToken();
    const response = await accountRequest(`${apiBase}/api/account/records/household/${id}`, token, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id,
        display_name: displayName.trim(),
        provider_code: providerCode.trim(),
        service_region: region.trim() || null,
        created_at: now,
        updated_at: now,
      }),
    });
    setBusy(false);
    if (!response.ok || !response.body || typeof response.body !== "object") {
      setNotice(t("account.notSaved"));
      return;
    }
    if (!existing) {
      window.localStorage.setItem("bijlibachat.meter-household.v1", id);
    }
    const status = (response.body as { status?: string }).status;
    setNotice(t(status === "already_present" ? "account.already" : "account.saved"));
  }

  async function download() {
    if (!apiBase || view.mode !== "cloud" || view.phase !== "signed-in") {
      setNotice(t("account.exportFailed"));
      return;
    }
    const token = await auth.getToken();
    const response = await accountRequest(`${apiBase}/api/account/export`, token);
    if (!response.ok) {
      setNotice(t("account.exportFailed"));
      return;
    }
    const blob = new Blob([JSON.stringify(response.body, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "bijlibachat-account.json";
    link.click();
    URL.revokeObjectURL(url);
  }

  async function removeCloud() {
    if (!apiBase || !confirmDelete || view.mode !== "cloud" || view.phase !== "signed-in") {
      return;
    }
    setBusy(true);
    const token = await auth.getToken();
    const response = await accountRequest(
      `${apiBase}/api/account/data?include_login=${includeLogin ? "true" : "false"}`,
      token,
      { method: "DELETE" },
    );
    setBusy(false);
    setConfirmDelete(false);
    if (!response.ok || !response.body || typeof response.body !== "object") {
      setNotice(t("account.deleteIncomplete", { detail: t("account.copyFailed") }));
      return;
    }
    const report = response.body as { complete?: boolean; limitations?: string[] };
    if (report.complete) {
      setNotice(t("account.deleteComplete"));
      return;
    }
    setNotice(t("account.deleteIncomplete", { detail: (report.limitations ?? []).join(" ") }));
  }

  return (
    <section aria-labelledby="account-heading" className="flex flex-col gap-4">
      <div>
        <h2 id="account-heading" className="font-display text-base font-semibold leading-snug">
          {t("account.title")}
        </h2>
      </div>
      <Card as="section">
        {view.mode === "local" ? (
          <>
            <SectionHeader as="h3" title={t("account.localTitle")} description={t("account.localBody")} />
          </>
        ) : null}
        {view.mode === "cloud" && view.phase === "loading" ? (
          <p role="status">{t("account.loading")}</p>
        ) : null}
        {view.mode === "cloud" && view.phase === "rejected" ? (
          <p role="alert">{t("account.rejected")}</p>
        ) : null}
        {view.mode === "cloud" && (view.phase === "signed-out" || view.phase === "rejected") ? (
          <form
            className="mt-4 flex flex-col gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              void submit("sign-in");
            }}
          >
            <p className="text-sm leading-6 text-muted">{t("account.cloudSignedOut")}</p>
            <Input
              label={t("account.email")}
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
            <Input
              label={t("account.password")}
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button type="submit" disabled={busy}>
                {busy ? t("account.working") : t("account.signIn")}
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={busy}
                onClick={() => void submit("register")}
              >
                {t("account.register")}
              </Button>
            </div>
          </form>
        ) : null}
        {view.mode === "cloud" && view.phase === "signed-in" ? (
          <div className="flex flex-col gap-4">
            <p>
              <bdi>{t("account.signedIn", { email: view.email })}</bdi>
            </p>
            <p className="text-sm leading-6 text-muted">{t("account.where")}</p>
            <Button type="button" variant="secondary" onClick={() => void auth.signOut()}>
              {t("account.signOut")}
            </Button>
            <form
              className="flex flex-col gap-4"
              onSubmit={(event) => {
                event.preventDefault();
                void saveHousehold();
              }}
            >
              <h3 className="font-display text-base font-semibold">{t("account.householdTitle")}</h3>
              <p className="text-sm leading-6 text-muted">{t("account.householdHint")}</p>
              <Input label={t("account.displayName")} required value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              <Input label={t("account.provider")} required value={providerCode} onChange={(event) => setProviderCode(event.target.value)} />
              <Input label={t("account.region")} value={region} onChange={(event) => setRegion(event.target.value)} />
              <Button type="submit" disabled={busy}>
                {t("account.saveHousehold")}
              </Button>
            </form>
            <div>
              <h3 className="font-display text-base font-semibold">{t("account.copyTitle")}</h3>
              <p className="mt-1 text-sm leading-6 text-muted">{t("account.copyBody")}</p>
              {plan && plan.counts.every((item) => item.count === 0) ? (
                <p className="mt-2 text-sm">{t("account.copyEmpty")}</p>
              ) : (
                <ul className="mt-2 text-sm leading-6">
                  {plan?.counts.map((item) => (
                    <li key={item.collection}>
                      {t(collectionKey[item.collection])}: {item.count}
                    </li>
                  ))}
                </ul>
              )}
              <Button type="button" className="mt-3" disabled={busy} onClick={() => void copyRecords()}>
                {t("account.copyAction")}
              </Button>
            </div>
            <Button type="button" variant="secondary" onClick={() => void download()}>
              {t("account.export")}
            </Button>
            <div>
              <h3 className="font-display text-base font-semibold">{t("account.deleteTitle")}</h3>
              <p className="mt-1 text-sm leading-6 text-muted">{t("account.deleteBody")}</p>
              <label className="mt-3 flex min-h-12 items-center gap-3 text-sm">
                <input type="checkbox" className="h-5 w-5" checked={includeLogin} onChange={(event) => setIncludeLogin(event.target.checked)} />
                {t("account.deleteLogin")}
              </label>
              <label className="flex min-h-12 items-center gap-3 text-sm">
                <input type="checkbox" className="h-5 w-5" checked={confirmDelete} onChange={(event) => setConfirmDelete(event.target.checked)} />
                {t("account.deleteConfirm")}
              </label>
              <Button type="button" variant="danger" disabled={!confirmDelete || busy} onClick={() => void removeCloud()}>
                {t("account.deleteAction")}
              </Button>
            </div>
          </div>
        ) : null}
        {notice ? (
          <p className="mt-4 text-sm leading-6" role="status">
            {notice}
          </p>
        ) : null}
      </Card>
      <Card as="section">
        <h3 className="font-display text-base font-semibold">{t("account.resetTitle")}</h3>
        <p className="mt-1 text-sm leading-6 text-muted">{t("account.resetBody")}</p>
        <label className="mt-3 flex min-h-12 items-center gap-3 text-sm">
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={confirmReset}
            onChange={(event) => setConfirmReset(event.target.checked)}
          />
          {t("account.resetConfirm")}
        </label>
        <Button
          type="button"
          variant="secondary"
          disabled={!confirmReset}
          onClick={() => {
            clearDeviceRecords(window.localStorage);
            setConfirmReset(false);
            setPlan(recordsFromLocal(window.localStorage));
            setNotice(t("account.resetDone"));
          }}
        >
          {t("account.resetAction")}
        </Button>
      </Card>
    </section>
  );
}
