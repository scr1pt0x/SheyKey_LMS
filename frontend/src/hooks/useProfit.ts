import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";
import {
  expenseCreateSchema,
  expenseSchema,
  investorCreateSchema,
  investorSchema,
  investorSummarySchema,
  investorUpdateSchema,
  profitCalculateSchema,
  profitPeriodSchema,
  type Expense,
  type ExpenseCreateForm,
  type Investor,
  type InvestorCreateForm,
  type InvestorSummary,
  type InvestorUpdateForm,
  type ProfitCalculateForm,
  type ProfitPeriod,
} from "@/lib/schemas/profit";

export type {
  DistributionItem,
} from "@/lib/schemas/profit";

export type { Expense, ExpenseCreateForm, Investor, InvestorCreateForm, InvestorSummary, InvestorUpdateForm, ProfitCalculateForm, ProfitPeriod };

// ─── Investors ───────────────────────────────────────────────────────────────

export function useInvestors(includeInactive = false) {
  return useQuery({
    queryKey: ["investors", includeInactive],
    queryFn: async () => {
      const { data } = await api.get("/api/director/profit/investors", {
        params: { include_inactive: includeInactive },
      });
      return zodArray(investorSchema, data);
    },
  });
}

export function useInvestorSummary() {
  return useQuery({
    queryKey: ["investors", "summary"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/profit/investors/summary");
      return investorSummarySchema.parse(data);
    },
  });
}

export function useCreateInvestor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: InvestorCreateForm) => {
      const parsed = investorCreateSchema.parse(body);
      const { data } = await api.post("/api/director/profit/investors", parsed);
      return investorSchema.parse(data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["investors"] }),
  });
}

export function useUpdateInvestor(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: InvestorUpdateForm) => {
      const parsed = investorUpdateSchema.parse(body);
      const { data } = await api.patch(`/api/director/profit/investors/${id}`, parsed);
      return investorSchema.parse(data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["investors"] }),
  });
}

export function useDeactivateInvestor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/director/profit/investors/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["investors"] }),
  });
}

// ─── Expenses ────────────────────────────────────────────────────────────────

export function useExpenses(dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["expenses", dateFrom, dateTo],
    queryFn: async () => {
      const { data } = await api.get("/api/director/profit/expenses", {
        params: { date_from: dateFrom, date_to: dateTo },
      });
      return zodArray(expenseSchema, data);
    },
  });
}

export function useExpensesTotal(dateFrom: string, dateTo: string) {
  return useQuery({
    queryKey: ["expenses-total", dateFrom, dateTo],
    queryFn: async () => {
      const { data } = await api.get("/api/director/profit/expenses/total", {
        params: { date_from: dateFrom, date_to: dateTo },
      });
      return data as { by_category: Record<string, number>; total: number };
    },
    enabled: !!dateFrom && !!dateTo,
  });
}

export function useCreateExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ExpenseCreateForm) => {
      const parsed = expenseCreateSchema.parse(body);
      const { data } = await api.post("/api/director/profit/expenses", parsed);
      return expenseSchema.parse(data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["expenses"] }),
  });
}

export function useDeleteExpense() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/director/profit/expenses/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["expenses"] }),
  });
}

// ─── Profit periods ──────────────────────────────────────────────────────────

export function useProfitPeriods() {
  return useQuery({
    queryKey: ["profit-periods"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/profit/periods");
      return zodArray(profitPeriodSchema, data);
    },
  });
}

export function useCalculatePeriod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: ProfitCalculateForm) => {
      const parsed = profitCalculateSchema.parse(body);
      const { data } = await api.post("/api/director/profit/calculate", parsed);
      return profitPeriodSchema.parse(data);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profit-periods"] }),
  });
}

export function useApprovePeriod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (periodId: string) => {
      const { data } = await api.post(`/api/director/profit/periods/${periodId}/approve`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profit-periods"] }),
  });
}

export function useDeleteProfitPeriod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (periodId: string) => {
      const { data } = await api.delete(`/api/director/profit/periods/${periodId}`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profit-periods"] }),
  });
}

function zodArray<T>(schema: { parse: (v: unknown) => T }, data: unknown): T[] {
  if (!Array.isArray(data)) return [];
  return data.map((item) => schema.parse(item));
}
