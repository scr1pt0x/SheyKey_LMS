import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import api from "@/lib/axios";
import type { MurabahaQuote, MurabahaTariffOptions } from "@/lib/murabaha";

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
  params?: Record<string, unknown> | null;
}

export function useMurabahaTariffOptions(
  category: string,
  amount: number,
  enabled = true
) {
  return useQuery({
    queryKey: ["murabaha-tariff-options", category, amount],
    queryFn: async () => {
      const { data } = await api.get("/api/deals/murabaha/tariff-options", {
        params: { category, amount },
      });
      return data as MurabahaTariffOptions;
    },
    enabled: enabled && !!category && amount > 0,
  });
}

export function useMurabahaQuote(
  params: {
    category: string;
    amount: number;
    term: number;
    tariff: string;
    down_pct: number;
  } | null
) {
  return useQuery({
    queryKey: ["murabaha-quote", params],
    queryFn: async () => {
      const { data } = await api.get("/api/deals/murabaha/quote", { params: params! });
      return data as MurabahaQuote;
    },
    enabled:
      !!params &&
      params.amount > 0 &&
      params.term > 0 &&
      !!params.tariff &&
      params.down_pct >= 0,
  });
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

async function downloadBlobPost(url: string, filename: string): Promise<void> {
  try {
    const { data } = await api.post(url, {}, { responseType: "blob" });
    const blobUrl = URL.createObjectURL(data as Blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(blobUrl);
  } catch (err) {
    if (axios.isAxiosError(err) && err.response?.data instanceof Blob) {
      const text = await (err.response.data as Blob).text();
      try {
        const json = JSON.parse(text) as { detail?: string };
        if (typeof json.detail === "string") {
          throw new Error(json.detail);
        }
      } catch (parseErr) {
        if (parseErr instanceof Error && !(parseErr instanceof SyntaxError)) {
          throw parseErr;
        }
      }
    }
    throw err;
  }
}

export async function downloadMurabahaDocx(dealId: string): Promise<void> {
  return downloadBlobPost(
    `/api/documents/generate/murabaha-docx/${dealId}`,
    `murabaha_${dealId}.zip`
  );
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
