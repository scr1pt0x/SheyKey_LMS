import type { UserRole } from "@/store/auth";

export const ROLE_HOME: Record<UserRole, string> = {
  manager: "/dashboard",
  sb: "/sb/dashboard",
  director: "/director/dashboard",
};
