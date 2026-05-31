import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";

export interface OverdueCase {
  id: string;
  deal_id: string;
  sb_user_id: string | null;
  status: "new" | "in_progress" | "agreed" | "closed";
  assigned_at: string | null;
  closed_at: string | null;
  total_debt: string;
  days_overdue: number;
  created_at: string;
  updated_at: string;
  is_red_zone?: boolean;
  internal_notes?: string | null;
  client_name?: string | null;
  client_phone?: string | null;
}

export interface SbTodayWorkItem {
  case_id: string;
  deal_id: string;
  total_debt: string | number;
  days_overdue: number;
  status: string;
  last_contact_at?: string | null;
  promised_date?: string | null;
  promised_amount?: string | number | null;
  promise_id?: string | null;
}

export interface SbCaseContext {
  client_id: string;
  client_name: string;
  client_phone: string | null;
  manager_id: string;
  manager_name: string;
  deal_type: string;
  deal_status: string;
  deal_total: string | number;
  product_description: string | null;
  purchase_summary: string;
  next_schedule_due_date: string | null;
  next_schedule_amount: string | number | null;
  pending_schedules: PaymentScheduleBrief[];
}

export interface PaymentScheduleBrief {
  id: string;
  installment_number: number;
  due_date: string;
  amount: string;
  paid_amount: string;
  status: string;
}

export interface ContactLog {
  id: string;
  case_id: string;
  sb_user_id: string;
  type: "call" | "meeting" | "sms" | "telegram" | "other";
  result: string;
  next_action: string | null;
  next_action_date: string | null;
  created_at: string;
}

export interface PaymentPromise {
  id: string;
  case_id: string;
  promised_date: string;
  promised_amount: string;
  is_fulfilled: boolean;
  created_at: string;
}

export interface SbDashboard {
  my_cases_new: number;
  my_cases_in_progress: number;
  my_cases_agreed: number;
  my_cases_closed: number;
  promises_today: number;
  promises_this_week: number;
  recovered_this_month: string;
  red_zone_cases: number;
  unassigned_cases_total: number;
}

export function useOverdueCases(params: Record<string, unknown> = {}) {
  return useQuery({
    queryKey: ["sb-cases", params],
    queryFn: async () => {
      const { data } = await api.get("/api/sb/cases", { params });
      return data as { items: OverdueCase[]; total: number; limit: number; offset: number };
    },
  });
}

export function useOverdueCase(id: string) {
  return useQuery({
    queryKey: ["sb-cases", id],
    queryFn: async () => {
      const { data } = await api.get(`/api/sb/cases/${id}`);
      return data as OverdueCase;
    },
    enabled: !!id,
  });
}

export function useContactLogs(caseId: string) {
  return useQuery({
    queryKey: ["contact-logs", caseId],
    queryFn: async () => {
      const { data } = await api.get(`/api/sb/cases/${caseId}/contacts`);
      return data as ContactLog[];
    },
    enabled: !!caseId,
  });
}

export function useAddContactLog(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Omit<ContactLog, "id" | "case_id" | "sb_user_id" | "created_at">) => {
      const { data } = await api.post(`/api/sb/cases/${caseId}/contacts`, body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contact-logs", caseId] }),
  });
}

export function usePaymentPromises(caseId: string) {
  return useQuery({
    queryKey: ["promises", caseId],
    queryFn: async () => {
      const { data } = await api.get(`/api/sb/cases/${caseId}/promises`);
      return data as PaymentPromise[];
    },
    enabled: !!caseId,
  });
}

export function useAddPromise(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: { promised_date: string; promised_amount: string }) => {
      const { data } = await api.post(`/api/sb/cases/${caseId}/promises`, body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["promises", caseId] }),
  });
}

export function useSbDashboard() {
  return useQuery({
    queryKey: ["sb-dashboard"],
    queryFn: async () => {
      const { data } = await api.get("/api/sb/dashboard");
      return data as SbDashboard;
    },
  });
}

export function useSbTodayWork() {
  return useQuery({
    queryKey: ["sb-dashboard-today"],
    queryFn: async () => {
      const { data } = await api.get("/api/sb/dashboard/today");
      return data as {
        red_zone_cases: SbTodayWorkItem[];
        promises_today: SbTodayWorkItem[];
        promises_overdue: SbTodayWorkItem[];
        unassigned_top: SbTodayWorkItem[];
      };
    },
  });
}

export function useSbCaseContext(caseId: string) {
  return useQuery({
    queryKey: ["sb-case-context", caseId],
    queryFn: async () => {
      const { data } = await api.get(`/api/sb/cases/${caseId}/context`);
      return data as SbCaseContext;
    },
    enabled: !!caseId,
  });
}

export function useSbStats(dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["sb-stats", dateFrom, dateTo],
    queryFn: async () => {
      const { data } = await api.get("/api/sb/stats", {
        params: { date_from: dateFrom, date_to: dateTo },
      });
      return data as {
        cases_closed: number;
        promises_fulfilled_amount: string | number;
        avg_days_overdue_closed: number | null;
      };
    },
  });
}

export function useSbPromisesCalendar(dateFrom: string, dateTo: string) {
  return useQuery({
    queryKey: ["sb-promises-calendar", dateFrom, dateTo],
    queryFn: async () => {
      const { data } = await api.get("/api/sb/promises/calendar", {
        params: { date_from: dateFrom, date_to: dateTo },
      });
      return data as {
        promise_id: string;
        case_id: string;
        deal_id: string;
        promised_date: string;
        promised_amount: number;
        total_debt: number;
      }[];
    },
    enabled: !!dateFrom && !!dateTo,
  });
}

export function useUpdateCaseNotes(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (internal_notes: string | null) => {
      const { data } = await api.patch(`/api/sb/cases/${caseId}/notes`, { internal_notes });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sb-cases", caseId] });
    },
  });
}

export function useAssignCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ caseId, sb_user_id }: { caseId: string; sb_user_id: string }) => {
      const { data } = await api.patch(`/api/sb/cases/${caseId}/assign`, { sb_user_id });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sb-cases"] });
      qc.invalidateQueries({ queryKey: ["sb-dashboard"] });
      qc.invalidateQueries({ queryKey: ["sb-dashboard-today"] });
      qc.invalidateQueries({ queryKey: ["sb-control"] });
      qc.invalidateQueries({ queryKey: ["analytics", "sb-performance"] });
    },
  });
}

export function useTakeCase() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (caseId: string) => {
      const { data } = await api.post(`/api/sb/cases/${caseId}/take`);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sb-cases"] });
      qc.invalidateQueries({ queryKey: ["sb-dashboard"] });
      qc.invalidateQueries({ queryKey: ["sb-dashboard-today"] });
    },
  });
}

export function useUpdateCaseStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ caseId, status }: { caseId: string; status: string }) => {
      const { data } = await api.patch(`/api/sb/cases/${caseId}/status`, { status });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sb-cases"] }),
  });
}
