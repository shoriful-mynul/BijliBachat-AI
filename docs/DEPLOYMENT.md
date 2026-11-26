# Deployment

This document prepares BijliBachat AI for a hosted frontend and API. It does not record a live deployment. No production project was created from this repository, and no dashboard credentials were available here.

## Architecture

The repository is two applications that already have separate build commands.

| Piece | Host | Why this host |
| --- | --- | --- |
| Next.js frontend | Vercel | The app is an App Router project with `next build`. Vercel runs that build, serves HTTPS, and injects `NEXT_PUBLIC_*` at build time. |
| FastAPI backend | Render web service | The API is Python, starts with Uvicorn, and reads a platform `PORT`. Render runs a Python web service over HTTPS without adding another database. |
| Identity, records, and optional files | Firebase | Authentication, Firestore, and Storage are already integrated. The API uses the Admin SDK. The browser uses only the public client configuration. |

A single Node host cannot run the Python calculation services. A second database is not needed: household copies live in Firestore when Firebase is configured, and the browser keeps its own records when it is not.

## Modes

**Local/demo.** Firebase client settings and Admin credentials are empty. Settings says records stay in this browser. Sign-in is not offered. Overview figures stay labeled demo data. Calculation routes work against a local API. Clearing browser records does not call Firebase.

**Configured development.** `APP_ENV=development`. CORS may include `http://localhost:3000` and `http://127.0.0.1:3000`. Admin credentials, when present, turn on account routes. A storage bucket, when present, turns on explicit file retention. Health still does not call Firebase or Gemini.

**Production.** `APP_ENV=production`. Every CORS origin must be `https://` and explicit. A wildcard is rejected. The API listens on `0.0.0.0` and the host's `PORT`. Account routes require a verified Firebase token. Missing Firebase settings keep account writes unavailable; they do not pretend a save succeeded.

## Frontend on Vercel

1. Import `shoriful-mynul/BijliBachat-AI`.
2. Set the root directory to `frontend`.
3. Framework preset: Next.js. Build command: `npm run build`. Install command: `npm ci`. Output is the default Next.js output.
4. Set environment variables before the first production build. `NEXT_PUBLIC_*` values are baked into the client bundle:
   - `NEXT_PUBLIC_API_URL` — the Render HTTPS origin, with no trailing path. Example: `https://bijlibachat-api.onrender.com`.
   - `NEXT_PUBLIC_FIREBASE_API_KEY`
   - `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`
   - `NEXT_PUBLIC_FIREBASE_PROJECT_ID`
   - `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`
   - `NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID`
   - `NEXT_PUBLIC_FIREBASE_APP_ID`
5. Leave every Firebase variable empty to ship local/demo mode. The screen must not be given a partial set: one missing value keeps sign-in off.
6. Redeploy after changing any `NEXT_PUBLIC_*` value. Vercel does not pick those up until the next build.
7. Copy the Vercel HTTPS origin, for example `https://bijlibachat.vercel.app`, into the API `CORS_ORIGINS` and into Firebase Authentication's authorized domains.

The browser calls `getApiBaseUrl()`. A value that does not start with `http://` or `https://` is treated as missing. Production should use the `https://` API origin. There is no hardcoded production localhost URL.

## Backend on Render

1. New Web Service from the same repository.
2. Root directory: `backend`.
3. Runtime: Python 3.12.
4. Build command: `pip install -e .`
5. Start command, also written in `backend/Procfile`:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Render sets `PORT`. The process must bind `0.0.0.0`, not only localhost.

6. Environment variables:

| Variable | Required in production | Notes |
| --- | --- | --- |
| `APP_ENV` | Yes | `production` |
| `CORS_ORIGINS` | Yes | Comma-separated HTTPS origins only. Example: `https://bijlibachat.vercel.app`. No `*`. |
| `GEMINI_API_KEY` | No | Empty disables live bill and meter reading. The API returns 503 and does not invent fields. |
| `GEMINI_MODEL` | No | Default `gemini-3.8-flash` |
| `GEMINI_TIMEOUT_SECONDS` | No | Default 45, between 5 and 120 |
| `FIREBASE_PROJECT_ID` | No | All three Admin values are required together before account routes accept tokens |
| `FIREBASE_CLIENT_EMAIL` | No | Service-account email. Server only |
| `FIREBASE_PRIVATE_KEY` | No | See the private-key note below |
| `FIREBASE_STORAGE_BUCKET` | No | Without it, file retention stays off even when Auth and Firestore are on |
| `EXTRACT_RATE_LIMIT_PER_MINUTE` | No | Default 60. `0` disables the in-process file-check limit |
| `TRUSTED_PROXIES` | No | Comma-separated proxy IP addresses. Empty ignores `X-Forwarded-For` |

`FIREBASE_PRIVATE_KEY` is one line in the dashboard. Paste the key with escaped newlines (`\n`) between the `BEGIN` and `END` lines. The API turns those two-character sequences back into real newlines. Do not commit the key, a service-account JSON file, or `backend/.env`.

The in-process limiter is not shared across Render instances. It is not a distributed abuse control. `X-Forwarded-For` is used only when the immediate peer address is listed in `TRUSTED_PROXIES`. Set that to the proxy address Render presents to the app if you need the original client in the key. An untrusted caller cannot rotate the key by sending the header.

Health check path: `GET /health` is not used. The route is `GET /api/health`. `status: "ok"` means the process answered. Firebase, Gemini, and a complete payable tariff stay `not_configured` because this route does not call them.

## Firebase project

1. Create a Firebase project. This repository does not contain one.
2. Authentication → Sign-in method → enable Email/Password. Do not add other providers for this version.
3. Authentication → Settings → authorized domains: add the Vercel domain. `localhost` can stay for development.
4. Create a Cloud Firestore database.
5. Storage: create a bucket only if explicit file retention should be on. Copy the bucket name into both `FIREBASE_STORAGE_BUCKET` and `NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET`. The browser does not upload with the client Storage SDK; the API writes with the Admin SDK after consent.
6. Project settings → service accounts → generate a private key. Put `project_id`, `client_email`, and `private_key` into the three backend variables. Do not place that JSON in the frontend or in Git.
7. Project settings → general → your apps → web app. Copy the public config into the `NEXT_PUBLIC_FIREBASE_*` variables.

### Rules

From the repository root, with the Firebase CLI logged in to the intended project:

```bash
npx firebase-tools deploy --only firestore:rules,storage
```

Run this only after `npm test` in `firebase/` has passed against the emulator. The rules files deny access by default. Do not replace them with open rules to make a client SDK call easier.

The Admin SDK bypasses rules. The API still checks the verified token and writes `owner_uid` itself.

## CI

`.github/workflows/ci.yml` runs on pull requests and on pushes to `main`:

- Frontend on Node.js 22: `npm ci`, `npm test`, `npm run lint`, `npx next typegen`, `npx tsc --noEmit`, `npm run build`. Node 20 cannot run the type-stripping test command. `LayoutProps` is generated by `next typegen`, so typecheck runs after that step.
- Backend: editable install, import `app.main`, `pytest`.
- Firebase rules: Java 21, `npm ci` in `firebase/`, then the emulator suite.

Ordinary CI does not receive production secrets. The rules job uses project id `demo-bijlibachat`, which the emulator accepts without a real project.

## Rollback

- Vercel: promote the previous deployment in the project’s Deployments list.
- Render: roll back to the previous successful deploy of the web service.
- Firebase rules: redeploy the last known rules file from Git. Do not leave the console in test mode.
- Environment variables: restoring a previous release does not restore a deleted secret. Keep the service-account key in the host’s secret store.

A rollback of the frontend does not delete Firestore documents. Account deletion remains the explicit control in Settings.

## Troubleshooting

| What you see | What to check |
| --- | --- |
| Browser says the API address is not configured | `NEXT_PUBLIC_API_URL` was empty at build time. Set it and redeploy the frontend. |
| Browser request fails with no CORS header | `CORS_ORIGINS` must be the exact Vercel origin, including `https://`, with no path and no wildcard. |
| API refuses to boot | Production with an `http://` origin raises a settings error. Use HTTPS. |
| Sign-in form never appears | One public Firebase variable is empty. That is local/demo mode. |
| Sign-in works and copy says nothing was saved | The API is missing Admin credentials. The failure is honest. Local records stay. |
| File checkbox returns “not stored” | `FIREBASE_STORAGE_BUCKET` is empty, the file failed the signature or size check, or consent was not `retain_in_account`. |
| Health shows Firebase unavailable | Expected. Health does not call Firebase. |
| Bill reading returns 503 | `GEMINI_API_KEY` is empty or the model timed out. No fields are invented. |
| File checks return 429 | The in-process limit was reached for that client address. |

## What was not deployed

No Vercel project, Render service, or Firebase project was created in this phase. There is no verified production URL. Cost figures are omitted because no account’s current pricing page was checked for a selected instance size.
