"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/axios";
import {
  useTopDebtors,
  useSbPerformance,
  useConversionFunnel,
} from "@/hooks/useDirector";
import { formatCurrency, OVERDUE_STATUS_LABELS, DEAL_TYPE_LABELS } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  FunnelChart,
  Funnel,
  LabelList,
} from "recharts";
import { Badge } from "@/components/ui/badge";

export default function AnalyticsPage() {
  const [activityDays, setActivityDays] = useState(30);
  const router = useRouter();

  const { data: debtors } = useTopDebtors(15);
  const { data: sbPerformance } = useSbPerformance();
  const { data: funnel } = useConversionFunnel();

  const { data: avgDeal } = useQuery({
    queryKey: ["analytics", "avg-deal"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/avg-deal");
      return data as { by_type: { type: string; avg_amount: number; count: number }[]; overall_avg: number };
    },
  });

  const { data: income } = useQuery({
    queryKey: ["analytics", "income"],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/income", { params: { months: 3 } });
      return data as { type: string; income: number; payment_count: number }[];
    },
  });

  const { data: teamActivity } = useQuery({
    queryKey: ["analytics", "team-activity", activityDays],
    queryFn: async () => {
      const { data } = await api.get("/api/director/analytics/team-activity", { params: { days: activityDays } });
      return data as { user_id: string; name: string; role: string; action_count: number; last_action: string | null; top_action: string | null }[];
    },
  });

  const funnelData = funnel
    ? [
        { name: "Черновики", value: funnel.draft, fill: "#94a3b8" },
        { name: "На согл.", value: funnel.pending, fill: "#f59e0b" },
        { name: "Активные", value: funnel.active, fill: "#22c55e" },
        { name: "Закрытые", value: funnel.closed, fill: "#3b82f6" },
        { name: "Просроченные", value: funnel.overdue, fill: "#ef4444" },
      ]
    : [];

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Аналитика</h1>

      {/* Conversion funnel */}
      {funnel && (
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold mb-4">Воронка сделок</h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {funnelData.map((item) => (
              <div key={item.name} className="text-center">
                <div
                  className="rounded-lg py-3 px-2 font-bold text-white text-lg"
                  style={{ backgroundColor: item.fill }}
                >
                  {item.value}
                </div>
                <p className="text-xs text-gray-500 mt-1">{item.name}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SB Performance */}
      {sbPerformance && sbPerformance.length > 0 && (
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold mb-4">Результативность СБ</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={sbPerformance} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="sb_name" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v/1000).toFixed(0)}k`} />
              <Tooltip />
              <Bar yAxisId="left" dataKey="cases_closed" fill="#22c55e" name="Закрыто дел" radius={[4, 4, 0, 0]} />
              <Bar yAxisId="right" dataKey="recovered_amount" fill="#1a3a5c" name="Взыскано" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b">
                  <th className="py-2 pr-4">Сотрудник</th>
                  <th className="py-2 pr-4">Всего дел</th>
                  <th className="py-2 pr-4">Закрыто</th>
                  <th className="py-2">Взыскано</th>
                </tr>
              </thead>
              <tbody>
                {(sbPerformance as { sb_name: string; cases_total: number; cases_closed: number; recovered_amount: string }[]).map((r) => (
                  <tr key={r.sb_name} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{r.sb_name}</td>
                    <td className="py-2 pr-4">{r.cases_total}</td>
                    <td className="py-2 pr-4">{r.cases_closed}</td>
                    <td className="py-2 font-semibold text-green-600">
                      {formatCurrency(r.recovered_amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Top debtors */}
      {debtors && debtors.length > 0 && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Топ просрочников</h2>
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
                {(debtors as { client_id: string; client_name: string; deal_id: string; total_debt: string; days_overdue: number; sb_status: string | null }[]).map((d) => (
                  <tr key={d.deal_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{d.client_name}</td>
                    <td className="px-4 py-3 font-semibold text-red-600">
                      {formatCurrency(d.total_debt)}
                    </td>
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
      {/* Average deal size */}
      {avgDeal && (
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold mb-3">Средний чек</h2>
          <div className="flex items-center gap-6 mb-4">
            <div>
              <p className="text-xs text-gray-500">Общий средний чек</p>
              <p className="text-2xl font-bold text-[#1a3a5c]">{formatCurrency(avgDeal.overall_avg)}</p>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {avgDeal.by_type.map((t) => (
              <div key={t.type} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 mb-1">{DEAL_TYPE_LABELS[t.type] ?? t.type}</p>
                <p className="font-bold">{formatCurrency(t.avg_amount)}</p>
                <p className="text-xs text-gray-400">{t.count} сделок</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Income by type */}
      {income && income.length > 0 && (
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold mb-4">Доходность за последние 3 месяца</h2>
          <div className="space-y-3">
            {income.map((i) => (
              <div key={i.type} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="font-medium">{DEAL_TYPE_LABELS[i.type] ?? i.type}</p>
                  <p className="text-xs text-gray-500">{i.payment_count} платежей</p>
                </div>
                <p className="text-lg font-bold text-green-600">{formatCurrency(i.income)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Team activity */}
      {teamActivity && teamActivity.length > 0 && (
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Активность команды</h2>
            <select
              value={activityDays}
              onChange={(e) => setActivityDays(Number(e.target.value))}
              className="px-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            >
              <option value={7}>7 дней</option>
              <option value={30}>30 дней</option>
              <option value={90}>90 дней</option>
            </select>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b">
                  <th className="py-2 pr-4">Сотрудник</th>
                  <th className="py-2 pr-4">Роль</th>
                  <th className="py-2 pr-4">Действий</th>
                  <th className="py-2">Последнее</th>
                </tr>
              </thead>
              <tbody>
                {teamActivity.map((u) => (
                  <tr key={u.user_id} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{u.name}</td>
                    <td className="py-2 pr-4 text-gray-500">
                      {u.role === "manager" ? "Менеджер" : u.role === "sb" ? "СБ" : "Руководитель"}
                    </td>
                    <td className="py-2 pr-4 font-medium">
                      {u.action_count} действий
                    </td>
                    <td className="py-2 text-xs text-gray-500">
                      {u.last_action ? new Date(u.last_action).toLocaleString("ru") : "—"}
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
