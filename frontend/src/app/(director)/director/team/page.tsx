"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTeam } from "@/hooks/useDirector";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Users, ArrowRightLeft, X } from "lucide-react";
import api from "@/lib/axios";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";

interface Manager {
  manager_id: string;
  manager_name: string;
  active_deals: number;
  overdue_deals: number;
  total_portfolio: string;
  last_activity: string | null;
}

export default function TeamPage() {
  const { data, isLoading } = useTeam();
  const qc = useQueryClient();

  // Reassign modal state
  const [showReassign, setShowReassign] = useState(false);
  const [fromManagerId, setFromManagerId] = useState("");
  const [toManagerId, setToManagerId] = useState("");
  const [reassignMode, setReassignMode] = useState<"all" | "overdue">("all");

  const managers = (data as Manager[] ?? []);

  const reassign = useMutation({
    mutationFn: async () => {
      if (!fromManagerId || !toManagerId || fromManagerId === toManagerId) return;
      // Get deals of the from-manager
      const { data: dealsData } = await api.get("/api/deals", {
        params: {
          manager_id: fromManagerId,
          status: reassignMode === "overdue" ? "overdue" : undefined,
          limit: 100,
        },
      });
      const dealIds = (dealsData.items as { id: string }[]).map((d) => d.id);

      const { data: clientsData } = await api.get("/api/clients", {
        params: { manager_id: fromManagerId, limit: 100 },
      });
      const clientIds = reassignMode === "all"
        ? (clientsData.items as { id: string }[]).map((c) => c.id)
        : [];

      await api.post("/api/director/team/reassign", {
        new_manager_id: toManagerId,
        deal_ids: dealIds,
        client_ids: clientIds,
      });
    },
    onSuccess: () => {
      toast({ title: "Перераспределение выполнено" });
      setShowReassign(false);
      setFromManagerId("");
      setToManagerId("");
      qc.invalidateQueries({ queryKey: ["director-team"] });
    },
    onError: (err) =>
      toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users size={22} className="text-[#1a3a5c]" />
          <h1 className="text-xl font-bold">Команда</h1>
        </div>
        <Button size="sm" variant="outline" onClick={() => setShowReassign(true)}>
          <ArrowRightLeft size={16} /> Перераспределить
        </Button>
      </div>

      {/* Reassign modal */}
      {showReassign && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Перераспределить клиентов / сделки</h2>
            <button onClick={() => setShowReassign(false)} className="text-gray-400 hover:text-gray-600">
              <X size={20} />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">С менеджера</label>
              <select
                value={fromManagerId}
                onChange={(e) => setFromManagerId(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              >
                <option value="">Выберите...</option>
                {managers.map((m) => (
                  <option key={m.manager_id} value={m.manager_id}>{m.manager_name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">На менеджера</label>
              <select
                value={toManagerId}
                onChange={(e) => setToManagerId(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              >
                <option value="">Выберите...</option>
                {managers.filter((m) => m.manager_id !== fromManagerId).map((m) => (
                  <option key={m.manager_id} value={m.manager_id}>{m.manager_name}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Что переносить</label>
            <div className="flex gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value="all"
                  checked={reassignMode === "all"}
                  onChange={() => setReassignMode("all")}
                  className="accent-[#1a3a5c]"
                />
                <span className="text-sm">Всех клиентов и сделки</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="mode"
                  value="overdue"
                  checked={reassignMode === "overdue"}
                  onChange={() => setReassignMode("overdue")}
                  className="accent-[#1a3a5c]"
                />
                <span className="text-sm">Только просроченные сделки</span>
              </label>
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              size="sm"
              loading={reassign.isPending}
              disabled={!fromManagerId || !toManagerId || fromManagerId === toManagerId}
              onClick={() => reassign.mutate()}
            >
              Выполнить перераспределение
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowReassign(false)}>
              Отмена
            </Button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {managers.map((manager) => (
            <div key={manager.manager_id} className="bg-white rounded-xl border p-5 space-y-3">
              <div>
                <p className="font-bold text-lg">{manager.manager_name}</p>
                {manager.last_activity && (
                  <p className="text-xs text-gray-500">
                    Активность: {formatDateTime(manager.last_activity)}
                  </p>
                )}
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-green-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-green-700">{manager.active_deals}</p>
                  <p className="text-xs text-gray-500">Активных</p>
                </div>
                <div className={`rounded-lg p-3 text-center ${manager.overdue_deals > 0 ? "bg-red-50" : "bg-gray-50"}`}>
                  <p className={`text-2xl font-bold ${manager.overdue_deals > 0 ? "text-red-600" : "text-gray-600"}`}>
                    {manager.overdue_deals}
                  </p>
                  <p className="text-xs text-gray-500">Просрочено</p>
                </div>
              </div>
              <div className="border-t pt-3">
                <p className="text-xs text-gray-500">Портфель</p>
                <p className="font-bold text-xl">{formatCurrency(manager.total_portfolio)}</p>
              </div>
            </div>
          ))}
          {!managers.length && (
            <p className="col-span-full text-center text-gray-500 py-8">Менеджеров нет</p>
          )}
        </div>
      )}
    </div>
  );
}
