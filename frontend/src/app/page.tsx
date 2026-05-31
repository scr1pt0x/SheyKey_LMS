"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

import { ROLE_HOME } from "@/lib/roleHome";

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
