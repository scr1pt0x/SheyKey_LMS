"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useManagerControl } from "@/hooks/useDirector";
import { formatCurrency, formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Briefcase, ArrowRightLeft, X } from "lucide-react";
import api from "@/lib/axios";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";

export interface ManagerControlRow {
  user_id: string;
  name: string;
  active_deals: number;
  overdue_deals: number;
  draft_deals: number;
  total_portfolio: string;
  overdue_pct: number;
  clients_count: number;
  payments_today: string;
  payments_week: string;
  payments_month: string;
  cash_month: string;
  deals_created_month: number;
  last_activity: string | null;
}

interface ActivityRow {
  user_id: string;
  name: string;
  role: string;
  action_count: number;
  last_action: string | null;
  top_action: string | null;
}

const INACTIVE_DAYS = 7;

function isInactive(lastActivity: string | null): boolean {
  if (!lastActivity) return true;
  const diff = Date.now() - new Date(lastActivity).getTime();
  return diff > INACTIVE_DAYS * 24 * 60 * 60 * 1000;
}

function rowHighlight(m: ManagerControlRow): string {
  if (m.overdue_deals > 0) return "bg-red-50/60";
  if (isInactive(m.last_activity)) return "bg-amber-50/60";
  return "";
}

export default function ManagersControlPage() {
  const { data, isLoading } = useManagerControl();
  const qc = useQueryClient();

  const [showReassign, setShowReassign] = useState(false);
  const [fromManagerId, setFromManagerId] = useState("");
  const [toManagerId, setToManagerId] = useState("");
  const [reassignMode, setReassignMode] = useState<"all" | "overdue">("all");

  const managers = (data as ManagerControlRow[] ?? []);

  const { data: activityRaw } = useQuery({
    queryKey: ["analytics", "team-activity", 30],
    queryFn: async () => {
      const { data: res } = await api.get("/api/director/analytics/team-activity", {
        params: { days: 30 },
      });
      return res as ActivityRow[];
    },
  });

  const activity = useMemo(
    () => (activityRaw ?? []).filter((u) => u.role === "manager"),
    [activityRaw]
  );

  const summary = useMemo(() => {
    const totalPortfolio = managers.reduce((s, m) => s + parseFloat(m.total_portfolio || "0"), 0);
    const totalOverdue = managers.reduce((s, m) => s + m.overdue_deals, 0);
    const totalActive = managers.reduce((s, m) => s + m.active_deals, 0);
    const paymentsMonth = managers.reduce((s, m) => s + parseFloat(m.payments_month || "0"), 0);
    const overduePct = totalActive + totalOverdue > 0
      ? Math.round((totalOverdue / (totalActive + totalOverdue)) * 1000) / 10
      : 0;
    return {
      count: managers.length,
      totalPortfolio,
      totalOverdue,
      overduePct,
      paymentsMonth,
    };
  }, [managers]);

  const reassign = useMutation({
    mutationFn: async () => {
      if (!fromManagerId || !toManagerId || fromManagerId === toManagerId) return;
      const { data: dealsData } = await api.get("/api/deals", {
        params: {
          manager_id: fromManagerId,
          status: reassignMode === "overdue" ? "overdue" : undefined,
          limit: 100,
        },
      });
      const dealIds = (dealsData.items as { id: string }[]).map((d) => d.id);

      const { data: clientsData } = await api.get("/api/clients", {
        params: { manager_id: fromManagerId, limit: 100, scope: "all" },
      });
      const clientIds = reassignMode === "all"
        ? (clientsData.items as { id: string }[]).map((c) => c.id)
        : [];

      await api.post("/api/director/managers/reassign", {
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
      qc.invalidateQueries({ queryKey: ["director-managers"] });
    },
    onError: (err) =>
      toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  return (
    <div className="space-y-5 w-full">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Briefcase size={22} className="text-[#1a3a5c]" />
          <h1 className="text-xl font-bold">Контроль менеджеров</h1>
        </div>
        <Button size="sm" variant="outline" onClick={() => setShowReassign(true)}>
          <ArrowRightLeft size={16} /> Перераспределить портфель
        </Button>
      </div>

      {showReassign && (
        <div className="bg-white rounded-xl border p-5 space-y-4 w-full">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Перераспределить клиентов / сделки</h2>
            <button type="button" onClick={() => setShowReassign(false)} className="text-gray-400 hover:text-gray-600">
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
                  <option key={m.user_id} value={m.user_id}>{m.name}</option>
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
                {managers.filter((m) => m.user_id !== fromManagerId).map((m) => (
                  <option key={m.user_id} value={m.user_id}>{m.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Что переносить</label>
            <div className="flex gap-3 flex-wrap">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="mode" checked={reassignMode === "all"} onChange={() => setReassignMode("all")} className="accent-[#1a3a5c]" />
                <span className="text-sm">Всех клиентов и сделки</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="radio" name="mode" checked={reassignMode === "overdue"} onChange={() => setReassignMode("overdue")} className="accent-[#1a3a5c]" />
                <span className="text-sm">Только просроченные сделки</span>
              </label>
            </div>
          </div>
          <div className="flex gap-3">
            <Button size="sm" loading={reassign.isPending} disabled={!fromManagerId || !toManagerId || fromManagerId === toManagerId} onClick={() => reassign.mutate()}>
              Выполнить перераспределение
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowReassign(false)}>Отмена</Button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Менеджеров" value={String(summary.count)} />
        <KpiCard label="Общий портфель" value={formatCurrency(summary.totalPortfolio)} />
        <KpiCard
          label="Просрочено"
          value={`${summary.totalOverdue} (${summary.overduePct}%)`}
          warn={summary.totalOverdue > 0}
        />
        <KpiCard label="Сборы за месяц" value={formatCurrency(summary.paymentsMonth)} accent />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : managers.length === 0 ? (
        <p className="text-center text-gray-500 py-8 bg-white rounded-xl border">Менеджеров нет</p>
      ) : (
        <>
          <div className="hidden md:block bg-white rounded-xl border overflow-x-auto w-full">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b text-xs text-gray-500">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">Менеджер</th>
                  <th className="text-right px-4 py-3 font-medium">Портфель</th>
                  <th className="text-right px-4 py-3 font-medium">Активных</th>
                  <th className="text-right px-4 py-3 font-medium">Просрочено</th>
                  <th className="text-right px-4 py-3 font-medium">Сборы сегодня</th>
                  <th className="text-right px-4 py-3 font-medium">Сборы месяц</th>
                  <th className="text-right px-4 py-3 font-medium">Черновики</th>
                  <th className="text-right px-4 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {managers.map((m) => (
                  <tr key={m.user_id} className={rowHighlight(m)}>
                    <td className="px-4 py-3">
                      <p className="font-medium">{m.name}</p>
                      <p className="text-xs text-gray-500">
                        {m.last_activity
                          ? formatDateTime(m.last_activity)
                          : "Нет активности"}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-right font-medium">{formatCurrency(m.total_portfolio)}</td>
                    <td className="px-4 py-3 text-right">{m.active_deals}</td>
                    <td className="px-4 py-3 text-right">
                      {m.overdue_deals > 0 ? (
                        <Badge className="bg-red-100 text-red-800">{m.overdue_deals}</Badge>
                      ) : (
                        "0"
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">{formatCurrency(m.payments_today)}</td>
                    <td className="px-4 py-3 text-right">{formatCurrency(m.payments_month)}</td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {m.draft_deals}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/deals?manager_id=${m.user_id}`} className="text-[#1a3a5c] hover:underline text-xs">
                        Сделки →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="md:hidden space-y-3">
            {managers.map((m) => (
              <div key={m.user_id} className={`bg-white rounded-xl border p-4 space-y-2 ${rowHighlight(m)}`}>
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-bold">{m.name}</p>
                    <p className="text-xs text-gray-500">
                      {m.last_activity ? formatDateTime(m.last_activity) : "Нет активности"}
                    </p>
                  </div>
                  <Link href={`/deals?manager_id=${m.user_id}`} className="text-[#1a3a5c] text-sm">Сделки →</Link>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-gray-500">Портфель:</span> {formatCurrency(m.total_portfolio)}</div>
                  <div><span className="text-gray-500">Активных:</span> {m.active_deals}</div>
                  <div><span className="text-gray-500">Просрочено:</span> {m.overdue_deals}</div>
                  <div><span className="text-gray-500">Сборы мес.:</span> {formatCurrency(m.payments_month)}</div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {activity.length > 0 && (
        <div className="bg-white rounded-xl border p-5 w-full">
          <h2 className="font-semibold mb-4">Активность за 30 дней</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b">
                  <th className="py-2 pr-4">Менеджер</th>
                  <th className="py-2 pr-4">Действий</th>
                  <th className="py-2 pr-4">Частое действие</th>
                  <th className="py-2">Последнее</th>
                </tr>
              </thead>
              <tbody>
                {activity.map((u) => (
                  <tr key={u.user_id} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{u.name}</td>
                    <td className="py-2 pr-4">{u.action_count}</td>
                    <td className="py-2 pr-4 text-gray-500">{u.top_action ?? "—"}</td>
                    <td className="py-2 text-xs text-gray-500">
                      {u.last_action ? formatDateTime(u.last_action) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  warn,
  accent,
}: {
  label: string;
  value: string;
  warn?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="bg-white rounded-xl border p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p
        className={`text-xl font-bold ${
          warn ? "text-red-600" : accent ? "text-green-600" : "text-gray-900"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
