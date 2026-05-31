"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthHydrated, useAuthStore, type UserRole } from "@/store/auth";
import { ROLE_HOME } from "@/lib/roleHome";

export function RequireRole({
  roles,
  children,
}: {
  roles: UserRole[];
  children: React.ReactNode;
}) {
  const user = useAuthStore((s) => s.user);
  const hasHydrated = useAuthHydrated();
  const router = useRouter();

  useEffect(() => {
    if (!hasHydrated) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!roles.includes(user.role)) {
      router.replace(ROLE_HOME[user.role]);
    }
  }, [user, roles, router, hasHydrated]);

  if (!hasHydrated) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user || !roles.includes(user.role)) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
      </div>
    );
  }

  return <>{children}</>;
}
