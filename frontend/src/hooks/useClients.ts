import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";

export interface Client {
  id: string;
  manager_id: string;
  manager_name?: string | null;
  full_name: string;
  phone: string;
  passport: string | null;
  address: string | null;
  kyc_status: "pending" | "verified" | "rejected";
  is_archived: boolean;
  notes: string | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface ClientListParams {
  q?: string;
  kyc_status?: string;
  manager_id?: string;
  is_archived?: boolean;
  limit?: number;
  offset?: number;
}

/** Lists are scoped on the server: managers see only their portfolio. */
export function useClients(params: ClientListParams = {}) {
  return useQuery({
    queryKey: ["clients", params],
    queryFn: async () => {
      const { data } = await api.get("/api/clients", { params });
      return data as { items: Client[]; total: number; limit: number; offset: number };
    },
  });
}

export function useClient(id: string) {
  return useQuery({
    queryKey: ["clients", id],
    queryFn: async () => {
      const { data } = await api.get(`/api/clients/${id}`);
      return data as Client;
    },
    enabled: !!id,
  });
}

export function useCreateClient() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Omit<Client, "id" | "manager_id" | "kyc_status" | "is_archived" | "created_at" | "updated_at">) => {
      const { data } = await api.post("/api/clients", body);
      return data as Client;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clients"] }),
  });
}

export function useUpdateClient(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<Client>) => {
      const { data } = await api.patch(`/api/clients/${id}`, body);
      return data as Client;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["clients", id] });
      qc.invalidateQueries({ queryKey: ["clients"] });
    },
  });
}

export function useArchiveClient() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/api/clients/${id}/archive`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clients"] }),
  });
}

export function useUpdateKyc(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (kyc_status: string) => {
      const { data } = await api.patch(`/api/clients/${id}/kyc`, { kyc_status });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["clients", id] }),
  });
}
