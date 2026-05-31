"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import api from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, formatDateTime, OVERDUE_STATUS_LABELS } from "@/lib/utils";
import { useSbPerformance, useSbPresence, useSbStaff, useTopDebtors } from "@/hooks/useDirector";
import { useAssignCase } from "@/hooks/useSb";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { AlertTriangle, Clock, RefreshCw, Shield } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  new: "bg-red-100 text-red-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  agreed: "bg-blue-100 text-blue-800",
  closed: "bg-green-100 text-green-800",
};

const LIMIT = 30;

interface CaseRow {
  id: string;
  deal_id: string;
  sb_user_id: string | null;
  sb_name: string;
  status: string;
  total_debt: number;
  days_overdue: number;
  last_contact: string | null;
  is_red_zone: boolean;
  created_at: string;
}

export default function SbControlPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const qc = useQueryClient();

  const syncCases = useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/api/director/sync-overdue-cases");
      return data as { synced_cases: number; created_cases: number; detail: string };
    },
    onSuccess: (result) => {
      toast({
        title: result.detail,
        description: `Синхронизировано: ${result.synced_cases}, создано новых: ${result.created_cases}`,
      });
      qc.invalidateQueries({ queryKey: ["sb-control"] });
      qc.invalidateQueries({ queryKey: ["sb-dashboard"] });
      qc.invalidateQueries({ queryKey: ["sb-cases"] });
    },
    onError: (err) => {
      toast({ title: "Ошибка синхронизации", description: getErrorMessage(err), variant: "destructive" });
    },
  });

  const { data, isLoading } = useQuery({
    queryKey: ["sb-control", statusFilter, offset],
    queryFn: async () => {
      const params: Record<string, unknown> = { limit: LIMIT, offset };
      if (statusFilter) params.status_filter = statusFilter;
      const { data } = await api.get("/api/director/sb-control", { params });
      return data as { items: CaseRow[]; total: number };
    },
  });

  const { data: performance } = useSbPerformance();
  const { data: topDebtors } = useTopDebtors(15);
  const { data: presence = [], isLoading: presenceLoading } = useSbPresence();
  const { data: sbStaff = [] } = useSbStaff();
  const assignCase = useAssignCase();

  const handleAssign = (caseId: string, sbUserId: string) => {
    if (!sbUserId) return;
    assignCase.mutate(
      { caseId, sb_user_id: sbUserId },
      {
        onSuccess: () => {
          toast({ title: "Сотрудник СБ назначен" });
          qc.invalidateQueries({ queryKey: ["sb-control"] });
        },
        onError: (err) =>
          toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
      }
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Shield size={22} className="text-[#1a3a5c]" />
          <h1 className="text-xl font-bold">Контроль Службы Безопасности</h1>
        </div>
        <Button
          size="sm"
          variant="outline"
          loading={syncCases.isPending}
          onClick={() => syncCases.mutate()}
        >
          <RefreshCw size={16} /> Обновить дела СБ
        </Button>
      </div>

      {/* SB presence today */}
      <div className="bg-white rounded-xl border p-4">
        <div className="flex items-center gap-2 mb-3">
          <Clock size={18} className="text-[#1a3a5c]" />
          <h2 className="font-semibold text-sm">Присутствие сегодня</h2>
        </div>
        {presenceLoading ? (
          <p className="text-sm text-gray-500">Загрузка…</p>
        ) : presence.length === 0 ? (
          <p className="text-sm text-gray-500">Нет активных сотрудников СБ</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b">
                  <th className="pb-2 pr-4 font-medium">Сотрудник</th>
                  <th className="pb-2 pr-4 font-medium">Начало дня</th>
                  <th className="pb-2 font-medium">Статус</th>
                </tr>
              </thead>
              <tbody>
                {presence.map((p) => (
                  <tr key={p.sb_user_id} className="border-b last:border-0">
                    <td className="py-2.5 pr-4 font-medium">{p.sb_name}</td>
                    <td className="py-2.5 pr-4">
                      {p.day_started_at ? formatDateTime(p.day_started_at) : "Не начинал"}
                    </td>
                    <td className="py-2.5">
                      {p.is_online ? (
                        <Badge className="bg-green-100 text-green-800 border-0">На работе</Badge>
                      ) : p.last_seen_at ? (
                        <span className="text-gray-600">
                          Ушёл: {formatDateTime(p.last_seen_at)}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* SB performance summary */}
      {performance && performance.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {(performance as { sb_name: string; cases_total: number; cases_closed: number; recovered_amount: string }[]).map((p) => (
            <div key={p.sb_name} className="bg-white rounded-xl border p-4">
              <p className="font-semibold text-sm">{p.sb_name}</p>
              <div className="flex gap-4 mt-2 text-sm">
                <div>
                  <span className="text-gray-500">Всего:</span>{" "}
                  <span className="font-medium">{p.cases_total}</span>
                </div>
                <div>
                  <span className="text-gray-500">Закрыто:</span>{" "}
                  <span className="font-medium text-green-600">{p.cases_closed}</span>
                </div>
                <div>
                  <span className="text-gray-500">Взыскано:</span>{" "}
                  <span className="font-medium text-[#1a3a5c]">{formatCurrency(p.recovered_amount)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {topDebtors && topDebtors.length > 0 && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Топ должников (дела СБ)</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Клиент</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Долг</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Дней</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">Статус дела</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(topDebtors as { client_name: string; deal_id: string; total_debt: string; days_overdue: number; sb_status: string | null }[]).map((d) => (
                  <tr key={d.deal_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{d.client_name}</td>
                    <td className="px-4 py-3 font-semibold text-red-600">{formatCurrency(d.total_debt)}</td>
                    <td className="px-4 py-3">{d.days_overdue}</td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      {d.sb_status ? (
                        <Badge className="bg-gray-100 text-gray-700">
                          {OVERDUE_STATUS_LABELS[d.sb_status] ?? d.sb_status}
                        </Badge>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl border p-4 flex gap-3 flex-wrap items-center">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setOffset(0); }}
          className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        >
          <option value="">Все статусы</option>
          {Object.entries(OVERDUE_STATUS_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
        {data && (
          <span className="text-sm text-gray-500">{data.total} дел</span>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-10">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : (
        <>
          {/* Mobile cards */}
          <div className="md:hidden space-y-2">
            {data?.items.map((c) => (
              <Link
                key={c.id}
                href={`/sb/cases/${c.id}`}
                className={`flex items-center gap-3 bg-white rounded-xl border p-4 hover:shadow-sm transition-shadow ${c.is_red_zone ? "border-red-300 bg-red-50" : ""}`}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className={STATUS_COLORS[c.status]}>{OVERDUE_STATUS_LABELS[c.status]}</Badge>
                    {c.is_red_zone && (
                      <span className="text-xs font-medium text-red-600 flex items-center gap-1">
                        <AlertTriangle size={12} /> Нет контакта
                      </span>
                    )}
                  </div>
                  <p className="text-lg font-bold text-red-600 mt-0.5">{formatCurrency(c.total_debt)}</p>
                  <p className="text-xs text-gray-500">{c.days_overdue} дн.</p>
                  <div className="mt-2" onClick={(e) => e.preventDefault()}>
                    <SbAssignSelect
                      caseId={c.id}
                      currentSbUserId={c.sb_user_id}
                      staff={sbStaff}
                      disabled={assignCase.isPending}
                      onAssign={handleAssign}
                    />
                  </div>
                  <p className="text-xs text-gray-400">
                    Последний контакт: {c.last_contact ? formatDateTime(c.last_contact) : "не было"}
                  </p>
                </div>
                <span className="text-gray-400">›</span>
              </Link>
            ))}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block bg-white rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Статус</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Долг</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Дней</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Сотрудник СБ</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Последний контакт</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Зона</th>
                  <th />
                </tr>
              </thead>
              <tbody className="divide-y">
                {data?.items.map((c) => (
                  <tr
                    key={c.id}
                    className={`hover:bg-gray-50 ${c.is_red_zone ? "bg-red-50 hover:bg-red-100" : ""}`}
                  >
                    <td className="px-4 py-3">
                      <Badge className={STATUS_COLORS[c.status]}>{OVERDUE_STATUS_LABELS[c.status]}</Badge>
                    </td>
                    <td className="px-4 py-3 font-semibold text-red-600">{formatCurrency(c.total_debt)}</td>
                    <td className="px-4 py-3 font-medium">{c.days_overdue}</td>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <SbAssignSelect
                        caseId={c.id}
                        currentSbUserId={c.sb_user_id}
                        staff={sbStaff}
                        disabled={assignCase.isPending}
                        onAssign={handleAssign}
                      />
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {c.last_contact ? formatDateTime(c.last_contact) : <span className="text-red-500">Не было</span>}
                    </td>
                    <td className="px-4 py-3">
                      {c.is_red_zone && (
                        <span className="flex items-center gap-1 text-red-600 text-xs font-medium">
                          <AlertTriangle size={14} /> Красная
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Link href={`/sb/cases/${c.id}`} className="text-[#1a3a5c] hover:underline text-xs font-medium">
                        Открыть →
                      </Link>
                    </td>
                  </tr>
                ))}
                {!data?.items.length && (
                  <tr><td colSpan={7} className="text-center py-8 text-gray-500">Дел нет</td></tr>
                )}
              </tbody>
            </table>
            {data && data.total > LIMIT && (
              <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
                <p className="text-sm text-gray-500">{data.total} дел</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setOffset(Math.max(0, offset - LIMIT))} disabled={offset === 0}>Назад</Button>
                  <Button size="sm" variant="outline" onClick={() => setOffset(offset + LIMIT)} disabled={offset + LIMIT >= data.total}>Далее</Button>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SbAssignSelect({
  caseId,
  currentSbUserId,
  staff,
  disabled,
  onAssign,
}: {
  caseId: string;
  currentSbUserId: string | null;
  staff: { id: string; name: string }[];
  disabled?: boolean;
  onAssign: (caseId: string, sbUserId: string) => void;
}) {
  if (staff.length === 0) {
    return (
      <span className="text-xs text-gray-500">
        {currentSbUserId ? "Назначен" : "Нет сотрудников СБ"}
      </span>
    );
  }

  return (
    <select
      value={currentSbUserId ?? ""}
      disabled={disabled}
      onChange={(e) => onAssign(caseId, e.target.value)}
      onClick={(e) => e.stopPropagation()}
      className="max-w-[11rem] w-full px-2 py-1.5 text-xs border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
      aria-label="Назначить сотрудника СБ"
    >
      {!currentSbUserId && <option value="">Не назначен</option>}
      {staff.map((u) => (
        <option key={u.id} value={u.id}>
          {u.name}
        </option>
      ))}
    </select>
  );
}
