"use client";

import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Auth } from "firebase/auth";
import type { PublicFirebaseConfig } from "@/lib/firebase/public-config";
import { sessionView, signInOutcome, type AuthFormResult, type SessionView } from "@/lib/firebase/session";

type AuthContextValue = {
  view: SessionView;
  signIn: (email: string, password: string) => Promise<AuthFormResult>;
  register: (email: string, password: string) => Promise<AuthFormResult>;
  signOut: () => Promise<void>;
  getToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  config: PublicFirebaseConfig | null;
  children: ReactNode;
};

export function AuthProvider({ config, children }: AuthProviderProps) {
  const authRef = useRef<Auth | null>(null);
  const [phase, setPhase] = useState<"loading" | "signed-out" | "signed-in" | "rejected">(
    config ? "loading" : "signed-out",
  );
  const [email, setEmail] = useState<string | null>(null);
  const configured = config !== null;

  useEffect(() => {
    if (!config) {
      return;
    }
    let unsubscribe = () => {};
    let cancelled = false;

    void (async () => {
      try {
        const { initializeApp, getApps } = await import("firebase/app");
        const { browserLocalPersistence, getAuth, onAuthStateChanged, setPersistence } = await import(
          "firebase/auth"
        );
        if (cancelled) {
          return;
        }
        const app = getApps()[0] ?? initializeApp(config);
        const auth = getAuth(app);
        await setPersistence(auth, browserLocalPersistence);
        if (cancelled) {
          return;
        }
        authRef.current = auth;
        unsubscribe = onAuthStateChanged(auth, (user) => {
          queueMicrotask(() => {
            if (cancelled) {
              return;
            }
            setEmail(user?.email ?? null);
            setPhase(user ? "signed-in" : "signed-out");
          });
        });
      } catch {
        queueMicrotask(() => {
          if (!cancelled) {
            setPhase("rejected");
          }
        });
      }
    })();

    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, [config]);

  const value = useMemo<AuthContextValue>(() => {
    const view = sessionView(configured, phase, email);

    async function run(action: "sign-in" | "register", address: string, password: string) {
      if (!configured || !authRef.current) {
        return signInOutcome(false, null);
      }
      try {
        const { createUserWithEmailAndPassword, signInWithEmailAndPassword } = await import("firebase/auth");
        if (action === "register") {
          await createUserWithEmailAndPassword(authRef.current, address, password);
        } else {
          await signInWithEmailAndPassword(authRef.current, address, password);
        }
        return signInOutcome(true, null);
      } catch (error) {
        const code = error && typeof error === "object" && "code" in error ? String(error.code) : "auth/unknown";
        if (code === "auth/user-token-expired" || code === "auth/invalid-user-token") {
          setPhase("rejected");
        }
        return signInOutcome(true, code);
      }
    }

    return {
      view,
      signIn: (address, password) => run("sign-in", address, password),
      register: (address, password) => run("register", address, password),
      signOut: async () => {
        if (!authRef.current) {
          return;
        }
        const { signOut } = await import("firebase/auth");
        await signOut(authRef.current);
      },
      getToken: async () => {
        const user = authRef.current?.currentUser;
        if (!user) {
          return null;
        }
        try {
          return await user.getIdToken();
        } catch {
          setPhase("rejected");
          return null;
        }
      },
    };
  }, [configured, email, phase]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("AuthProvider is missing");
  }
  return value;
}
