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
