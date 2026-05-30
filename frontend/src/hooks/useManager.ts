import { useQuery } from "@tanstack/react-query";
import api from "@/lib/axios";

export interface ManagerDashboard {
  active_deals: number;
  overdue_deals: number;
  pending_deals: number;
  draft_deals: number;
  portfolio_active_total: number | string;
  payments_today: number | string;
  payments_week: number | string;
  payments_month: number | string;
  clients_kyc_pending: number;
  deals_created_month: number;
  schedules_today: ScheduledPaymentBrief[];
  schedules_week: ScheduledPaymentBrief[];
  overdue_deals_list: DealBrief[];
  pending_deals_list: DealBrief[];
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
