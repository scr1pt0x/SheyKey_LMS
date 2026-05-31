import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";

export interface ScheduleItem {
  id: string;
  installment_number: number;
  due_date: string;
  amount: string;
  paid_amount: string;
  status: "pending" | "paid" | "overdue" | "partial";
  installment_type: string;
}

export interface Deal {
  id: string;
  client_id: string;
  manager_id: string;
  type: "murabaha" | "ijara";
  status: "draft" | "active" | "closed" | "overdue";
  principal: string;
  markup: string;
  total: string;
  duration_months: number;
  start_date: string | null;
  end_date: string | null;
  approved_by: string | null;
  approved_at: string | null;
  rejection_comment: string | null;
  product_description?: string | null;
  purchase_summary?: string | null;
  manager_name?: string | null;
  client_name?: string | null;
  created_at: string;
  updated_at?: string;
  payment_schedules?: ScheduleItem[];
}

export interface DealListParams {
  status?: string;
  type?: string;
  manager_id?: string;
  client_id?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

/** Lists are scoped on the server: managers see only their portfolio. */
export function useDeals(params: DealListParams = {}) {
  return useQuery({
    queryKey: ["deals", params],
    queryFn: async () => {
      const { data } = await api.get("/api/deals", { params });
      return data as { items: Deal[]; total: number; limit: number; offset: number };
    },
  });
}

export function useDeal(id: string, queryEnabled = true) {
  return useQuery({
    queryKey: ["deals", id],
    queryFn: async () => {
      const { data } = await api.get(`/api/deals/${id}`);
      return data as Deal & { payment_schedules: ScheduleItem[] };
    },
    enabled: queryEnabled && !!id,
  });
}

export function useCreateDeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: unknown) => {
      const { data } = await api.post("/api/deals", body);
      return data as Deal;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deals"] }),
  });
}

export function useSubmitDeal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/api/deals/${id}/submit`);
      return data;
    },
    onSuccess: (_d, id) => {
      qc.invalidateQueries({ queryKey: ["deals", id] });
      qc.invalidateQueries({ queryKey: ["deals"] });
    },
  });
}
