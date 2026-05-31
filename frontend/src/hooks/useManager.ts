import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";

export interface ManagerDashboard {
  active_deals: number;
  overdue_deals: number;
  draft_deals: number;
  portfolio_active_total: number | string;
  payments_today: number | string;
  payments_week: number | string;
  payments_month: number | string;
  deals_created_month: number;
  schedules_today: ScheduledPaymentBrief[];
  schedules_week: ScheduledPaymentBrief[];
  overdue_deals_list: DealBrief[];
}

export interface ScheduledPaymentBrief {
  schedule_id: string;
  deal_id: string;
  client_id: string;
  due_date: string;
  amount: number | string;
  status: string;
}

export interface DealBrief {
  id: string;
  client_id: string;
  type: string;
  status: string;
  total: number | string;
}

export function useManagerDashboard() {
  return useQuery({
    queryKey: ["manager-dashboard"],
    queryFn: async () => {
      const { data } = await api.get("/api/manager/dashboard");
      return data as ManagerDashboard;
    },
    staleTime: 60_000,
  });
}

export function useManagerStats(month?: string) {
  return useQuery({
    queryKey: ["manager-stats", month],
    queryFn: async () => {
      const { data } = await api.get("/api/manager/stats", {
        params: month ? { month } : undefined,
      });
      return data as { deals_created: number; payments_collected: number | string; bonus_note: string };
    },
  });
}

export interface CashLedgerItem {
  id: string;
  entry_type: "installment" | "manual" | "expense";
  amount: string | number;
  paid_at: string;
  method: string;
  description: string;
  deal_id?: string | null;
  client_name?: string | null;
}

export interface ManagerCashResponse {
  items: CashLedgerItem[];
  total: number;
  limit: number;
  offset: number;
  total_today: string | number;
  total_month: string | number;
  total_all_time: string | number;
}

export function useManagerCash(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["manager-cash", params],
    queryFn: async () => {
      const { data } = await api.get("/api/manager/cash", { params });
      return data as ManagerCashResponse;
    },
    staleTime: 30_000,
    retry: 1,
  });
}

export function useAddCashEntry() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      amount: string;
      paid_at: string;
      method: string;
      description: string;
      entry_kind: "income" | "expense";
    }) => {
      const { data } = await api.post("/api/manager/cash", body);
      return data as CashLedgerItem;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["manager-cash"] });
      qc.invalidateQueries({ queryKey: ["manager-stats"] });
    },
  });
}

/** @deprecated use useAddCashEntry */
export const useAddManualCashEntry = useAddCashEntry;
