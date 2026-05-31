"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthHydrated, useAuthStore } from "@/store/auth";

import { ROLE_HOME } from "@/lib/roleHome";

export default function HomePage() {
  const user = useAuthStore((s) => s.user);
  const hasHydrated = useAuthHydrated();
  const router = useRouter();

  useEffect(() => {
    if (!hasHydrated) return;
    if (user) {
      router.replace(ROLE_HOME[user.role] ?? "/clients");
    } else {
      router.replace("/login");
    }
  }, [user, router, hasHydrated]);

  return null;
}
