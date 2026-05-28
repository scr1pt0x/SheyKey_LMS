import { create } from "zustand";
import { persist } from "zustand/middleware";

export type UserRole = "manager" | "sb" | "director";

interface AuthUser {
  id: string;
  name: string;
  role: UserRole;
}

interface AuthState {
  user: AuthUser | null;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      logout: () => set({ user: null }),
    }),
    {
      name: "lms-auth",
      partialize: (state) => ({ user: state.user }),
    }
  )
);
