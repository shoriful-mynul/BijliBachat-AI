/** Public Firebase client configuration. Admin credentials never belong here. */

export type PublicFirebaseConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket: string;
  messagingSenderId: string;
  appId: string;
};

const fields = [
  ["apiKey", "NEXT_PUBLIC_FIREBASE_API_KEY"],
  ["authDomain", "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN"],
  ["projectId", "NEXT_PUBLIC_FIREBASE_PROJECT_ID"],
  ["storageBucket", "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET"],
  ["messagingSenderId", "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID"],
  ["appId", "NEXT_PUBLIC_FIREBASE_APP_ID"],
] as const;

export function readPublicFirebaseConfig(
  env: Record<string, string | undefined>,
): PublicFirebaseConfig | null {
  const config: Partial<PublicFirebaseConfig> = {};
  for (const [field, name] of fields) {
    const value = env[name]?.trim();
    if (!value) {
      return null;
    }
    config[field] = value;
  }
  return config as PublicFirebaseConfig;
}
