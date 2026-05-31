import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";

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

export function usePortfolioByType() {
  return useQuery({
    queryKey: ["analytics", "portfolio"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/portfolio");
      return data;
    },
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

export function useStaffUsers(role?: "manager" | "sb") {
  return useQuery({
    queryKey: ["staff-users", role ?? "all"],
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
      qc.invalidateQueries({ queryKey: ["director-team"] });
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
      qc.invalidateQueries({ queryKey: ["director-team"] });
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
      qc.invalidateQueries({ queryKey: ["director-team"] });
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

export function useTeam() {
  return useQuery({
    queryKey: ["director-team"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/team");
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

export function usePendingDeals() {
  return useQuery({
    queryKey: ["approval", "deals"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/approval/deals");
      return data;
    },
  });
}

export function usePendingRestructurings() {
  return useQuery({
    queryKey: ["approval", "restructurings"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/approval/restructurings");
      return data;
    },
  });
}

export function useApproveDeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ dealId, comment }: { dealId: string; comment?: string }) => {
      const { data } = await api.post(`/api/director/approval/deals/${dealId}/approve`, {
        comment: comment ?? "",
      });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["approval"] });
      qc.invalidateQueries({ queryKey: ["deals"] });
      qc.invalidateQueries({ queryKey: ["director-dashboard"] });
    },
  });
}

export function useRejectDeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ dealId, comment }: { dealId: string; comment: string }) => {
      const { data } = await api.post(`/api/director/approval/deals/${dealId}/reject`, { comment });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["approval"] }),
  });
}

export function useApproveRestructuring() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ rId, comment }: { rId: string; comment?: string }) => {
      const { data } = await api.post(`/api/director/approval/restructurings/${rId}/approve`, {
        comment: comment ?? "",
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["approval"] }),
  });
}

export function useRejectRestructuring() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ rId, comment }: { rId: string; comment: string }) => {
      const { data } = await api.post(`/api/director/approval/restructurings/${rId}/reject`, {
        comment,
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["approval"] }),
  });
}
