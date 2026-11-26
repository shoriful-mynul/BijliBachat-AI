/** Account API calls. The token is sent once per request and is not written into local records. */

export type AccountResponse = {
  ok: boolean;
  status: number;
  body: unknown;
};

export async function accountRequest(
  url: string,
  token: string | null,
  init: RequestInit = {},
): Promise<AccountResponse> {
  if (!token) {
    return { ok: false, status: 401, body: null };
  }
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  try {
    const response = await fetch(url, { ...init, headers });
    const body: unknown = await response.json().catch(() => null);
    return { ok: response.ok, status: response.status, body };
  } catch {
    return { ok: false, status: 0, body: null };
  }
}

export async function retainOriginal(
  apiBase: string,
  token: string | null,
  file: File,
  category: "bill" | "meter_photo",
): Promise<AccountResponse> {
  const body = new FormData();
  body.set("category", category);
  body.set("consent", "retain_in_account");
  body.set("file", file);
  return accountRequest(`${apiBase}/api/account/files`, token, { method: "POST", body });
}
