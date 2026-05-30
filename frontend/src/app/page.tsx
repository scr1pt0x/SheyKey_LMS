"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

const ROLE_HOME: Record<string, string> = {
  manager: "/dashboard",
  sb: "/sb/dashboard",
  director: "/director/dashboard",
};

export default function HomePage() {
  const user = useAuthStore((s) => s.user);
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.replace(ROLE_HOME[user.role] ?? "/clients");
    } else {
      router.replace("/login");
    }
  }, [user, router]);

  return null;
}
