import { create } from "zustand";
import { persist } from "zustand/middleware";
import { useEffect, useState } from "react";

export type UserRole = "manager" | "sb" | "director";

interface AuthUser {
  id: string;
  name: string;
  role: UserRole;
}

interface AuthState {
  user: AuthUser | null;
  _hasHydrated: boolean;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      _hasHydrated: false,
      setUser: (user) => set({ user }),
      logout: () => set({ user: null }),
      setHasHydrated: (value) => set({ _hasHydrated: value }),
    }),
    {
      name: "lms-auth",
      partialize: (state) => ({ user: state.user }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);

export function useAuthHydrated(): boolean {
  const hasHydrated = useAuthStore((s) => s._hasHydrated);
  const setHasHydrated = useAuthStore((s) => s.setHasHydrated);

  useEffect(() => {
    if (useAuthStore.persist.hasHydrated()) {
      setHasHydrated(true);
    }
    return useAuthStore.persist.onFinishHydration(() => {
      setHasHydrated(true);
    });
  }, [setHasHydrated]);

  return hasHydrated;
}
