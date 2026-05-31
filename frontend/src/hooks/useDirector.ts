import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";

export interface ManagerControlRow {
  user_id: string;
  name: string;
  active_deals: number;
  overdue_deals: number;
  draft_deals: number;
  total_portfolio: string;
  overdue_pct: number;
  clients_count: number;
  payments_today: string;
  payments_week: string;
  payments_month: string;
  cash_month: string;
  deals_created_month: number;
  last_activity: string | null;
}

export function useDirectorDashboard() {
  return useQuery({
    queryKey: ["director-dashboard"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/dashboard");
      return data;
    },
    staleTime: 15 * 60 * 1000,
  });
}

export function useIssuanceDynamics(months = 12) {
  return useQuery({
    queryKey: ["analytics", "issuance", months],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/issuance", { params: { months } });
      return data;
    },
  });
}

export function useTopDebtors(limit = 20) {
  return useQuery({
    queryKey: ["analytics", "top-debtors", limit],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/top-debtors", { params: { limit } });
      return data;
    },
  });
}

export function useSbPerformance() {
  return useQuery({
    queryKey: ["analytics", "sb-performance"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/sb-performance");
      return data;
    },
  });
}

export interface SbPresenceMember {
  sb_user_id: string;
  sb_name: string;
  day_started_at: string | null;
  last_seen_at: string | null;
  is_online: boolean;
}

export function useSbPresence() {
  return useQuery({
    queryKey: ["sb-presence"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/sb-presence");
      return data as SbPresenceMember[];
    },
    refetchInterval: 60_000,
  });
}

export interface SbStaffMember {
  id: string;
  name: string;
  is_active: boolean;
}

export function useSbStaff() {
  return useQuery({
    queryKey: ["sb-staff"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/users", {
        params: { role: "sb", limit: 100 },
      });
      return (data.items as SbStaffMember[]).filter((u) => u.is_active);
    },
    staleTime: 5 * 60 * 1000,
  });
}

export interface StaffUser {
  id: string;
  name: string;
  phone: string | null;
  role: "manager" | "sb" | "director";
  is_active: boolean;
  last_login: string | null;
}

export function useStaffUsers(
  role?: "manager" | "sb",
  options?: { enabled?: boolean }
) {
  return useQuery({
    queryKey: ["staff-users", role ?? "all"],
    enabled: options?.enabled ?? true,
    queryFn: async () => {
      const params: Record<string, unknown> = { limit: 100 };
      if (role) params.role = role;
      const { data } = await api.get("/api/director/users", { params });
      const items = data.items as StaffUser[];
      return items.filter((u) => u.role !== "director");
    },
  });
}

export function useCreateStaffUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      name: string;
      phone: string;
      role: "manager" | "sb";
      password: string;
    }) => {
      const { data } = await api.post("/api/director/users", body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["staff-users"] });
      qc.invalidateQueries({ queryKey: ["sb-staff"] });
      qc.invalidateQueries({ queryKey: ["director-managers"] });
    },
  });
}

export function useUpdateStaffUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userId,
      ...body
    }: {
      userId: string;
      name?: string;
      phone?: string;
      is_active?: boolean;
    }) => {
      const { data } = await api.patch(`/api/director/users/${userId}`, body);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["staff-users"] });
      qc.invalidateQueries({ queryKey: ["sb-staff"] });
      qc.invalidateQueries({ queryKey: ["director-managers"] });
    },
  });
}

export function useDeactivateStaffUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.delete(`/api/director/users/${userId}`);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["staff-users"] });
      qc.invalidateQueries({ queryKey: ["sb-staff"] });
      qc.invalidateQueries({ queryKey: ["director-managers"] });
    },
  });
}

export function usePortfolioByType() {
  return useQuery({
    queryKey: ["analytics", "portfolio"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/portfolio");
      return data as { type: string; count: number; total_amount: string; pct: number }[];
    },
  });
}

export function useOverdueDealsAnalytics(limit = 15) {
  return useQuery({
    queryKey: ["analytics", "overdue-deals", limit],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/overdue-deals", { params: { limit } });
      return data as {
        deal_id: string;
        client_id: string;
        client_name: string;
        manager_name: string;
        deal_total: string;
        days_overdue: number;
      }[];
    },
  });
}

export function useAnalyticsIncome(months = 3) {
  return useQuery({
    queryKey: ["analytics", "income", months],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/income", { params: { months } });
      return data as { type: string; income: number; payment_count: number }[];
    },
  });
}

export function useAnalyticsAvgDeal() {
  return useQuery({
    queryKey: ["analytics", "avg-deal"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/avg-deal");
      return data as { by_type: { type: string; avg_amount: number; count: number }[]; overall_avg: number };
    },
  });
}

export function useManagerActivity(days = 30) {
  return useQuery({
    queryKey: ["analytics", "team-activity", days, "manager"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/team-activity", { params: { days } });
      return (data as {
        user_id: string;
        name: string;
        role: string;
        action_count: number;
        last_action: string | null;
        top_action: string | null;
      }[]).filter((u) => u.role === "manager");
    },
  });
}

export function useConversionFunnel() {
  return useQuery({
    queryKey: ["analytics", "conversion"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/conversion");
      return data;
    },
  });
}

export function useManagerControl() {
  return useQuery<ManagerControlRow[]>({
    queryKey: ["director-managers"],
    queryFn: async () => {
      const { data } = await api.get<ManagerControlRow[]>("/api/director/managers/overview");
      return data;
    },
  });
}

export function useAuditLog(params: Record<string, unknown> = {}) {
  return useQuery({
    queryKey: ["audit-log", params],
    queryFn: async () => {
      const { data } = await api.get("/api/director/audit", { params });
      return data;
    },
  });
}
