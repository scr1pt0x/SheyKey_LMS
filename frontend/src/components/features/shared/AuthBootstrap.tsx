"use client";

import { useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";
import api from "@/lib/axios";
import { useAuthHydrated, useAuthStore, type UserRole } from "@/store/auth";

const PUBLIC_PATHS = ["/login"];

export function AuthBootstrap() {
  const hasHydrated = useAuthHydrated();
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const pathname = usePathname();
  const router = useRouter();
  const bootstrapped = useRef(false);

  useEffect(() => {
    if (!hasHydrated || user || bootstrapped.current) return;
    if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return;

    bootstrapped.current = true;

    api
      .get<{ id: string; name: string; role: UserRole }>("/api/auth/me")
      .then(({ data }) => {
        setUser({ id: data.id, name: data.name, role: data.role });
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [hasHydrated, user, setUser, pathname, router]);

  return null;
}
