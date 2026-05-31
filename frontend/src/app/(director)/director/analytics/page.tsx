"use client";

import { useState } from "react";
import Link from "next/link";
import {
  useDirectorDashboard,
  useIssuanceDynamics,
  usePortfolioByType,
  useManagerControl,
  useAnalyticsAvgDeal,
  useAnalyticsIncome,
  useConversionFunnel,
  useOverdueDealsAnalytics,
  useManagerActivity,
} from "@/hooks/useDirector";
import { formatCurrency, DEAL_TYPE_LABELS } from "@/lib/utils";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

const ACTION_LABELS: Record<string, string> = {
  CREATE: "Создание",
  UPDATE: "Изменение",
  STATUS_CHANGE: "Смена статуса",
  PAYMENT_RECORDED: "Платёж",
  LOGIN: "Вход",
};

export default function AnalyticsPage() {
  const [incomeMonths, setIncomeMonths] = useState(3);
  const [activityDays, setActivityDays] = useState(30);

  const { data: dashboard } = useDirectorDashboard();
  const { data: portfolio } = usePortfolioByType();
  const { data: dynamics } = useIssuanceDynamics(12);
  const { data: managers = [] } = useManagerControl();
  const { data: avgDeal } = useAnalyticsAvgDeal();
  const { data: income } = useAnalyticsIncome(incomeMonths);
  const { data: funnel } = useConversionFunnel();
  const { data: overdueDeals } = useOverdueDealsAnalytics(15);
  const { data: managerActivity } = useManagerActivity(activityDays);

  const funnelData = funnel
    ? [
        { name: "Черновики", value: funnel.draft, fill: "#94a3b8" },
        { name: "Активные", value: funnel.active, fill: "#22c55e" },
        { name: "Закрытые", value: funnel.closed, fill: "#3b82f6" },
        { name: "Просроченные", value: funnel.overdue, fill: "#ef4444" },
      ]
    : [];

  const portfolioChart = portfolio?.map((p) => ({
    name: DEAL_TYPE_LABELS[p.type] ?? p.type,
    amount: Number(p.total_amount),
    count: p.count,
  })) ?? [];

  const managerChart = managers.slice(0, 8).map((m) => ({
    name: m.name.split(" ")[0],
    portfolio: Number(m.total_portfolio),
    payments: Number(m.payments_month),
  }));

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Аналитика</h1>

      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Kpi label="Портфель" value={formatCurrency(dashboard.total_portfolio)} accent />
          <Kpi label="Активные" value={dashboard.active_deals} />
          <Kpi label="Просрочка" value={`${dashboard.overdue_pct}%`} warn={dashboard.overdue_pct > 10} />
          <Kpi label="Поступления месяц" value={formatCurrency(dashboard.cash_flow_month)} />
          <Kpi label="Новых сделок" value={dashboard.new_deals_month} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {portfolioChart.length > 0 && (
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold mb-4">Структура портфеля</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={portfolioChart} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} />
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
                <Bar dataKey="amount" fill="#1a3a5c" name="Сумма" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {portfolio?.map((p) => (
                <div key={p.type} className="text-sm bg-gray-50 rounded-lg p-2">
                  <p className="text-gray-500">{DEAL_TYPE_LABELS[p.type] ?? p.type}</p>
                  <p className="font-semibold">{formatCurrency(p.total_amount)}</p>
                  <p className="text-xs text-gray-400">{p.count} сделок · {p.pct}%</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {funnel && (
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold mb-4">Сделки по статусам</h2>
            <div className="grid grid-cols-2 gap-3">
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
      </div>

      {dynamics && dynamics.length > 0 && (
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold mb-4">Динамика выдач (12 мес.)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={dynamics} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="analyticsIssuance" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1a3a5c" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#1a3a5c" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} />
              <Tooltip formatter={(v: number) => formatCurrency(v)} />
              <Area
                type="monotone"
                dataKey="total_amount"
                stroke="#1a3a5c"
                strokeWidth={2}
                fill="url(#analyticsIssuance)"
                name="Объём"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {managers.length > 0 && (
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Сравнение менеджеров</h2>
            <Link href="/director/managers" className="text-sm text-[#1a3a5c] hover:underline">
              Подробнее →
            </Link>
          </div>
          {managerChart.length > 0 && (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={managerChart} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
                <Bar dataKey="portfolio" fill="#1a3a5c" name="Портфель" radius={[4, 4, 0, 0]} />
                <Bar dataKey="payments" fill="#22c55e" name="Сборы месяц" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b">
                  <th className="py-2 pr-4">Менеджер</th>
                  <th className="py-2 pr-4">Портфель</th>
                  <th className="py-2 pr-4">Просрочено</th>
                  <th className="py-2 pr-4">Сборы месяц</th>
                  <th className="py-2">Новых сделок</th>
                </tr>
              </thead>
              <tbody>
                {managers.map((m) => (
                  <tr key={m.user_id} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{m.name}</td>
                    <td className="py-2 pr-4">{formatCurrency(m.total_portfolio)}</td>
                    <td className="py-2 pr-4">{m.overdue_deals}</td>
                    <td className="py-2 pr-4">{formatCurrency(m.payments_month)}</td>
                    <td className="py-2">{m.deals_created_month}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {avgDeal && (
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold mb-3">Средний чек</h2>
            <p className="text-xs text-gray-500 mb-1">Общий средний чек</p>
            <p className="text-2xl font-bold text-[#1a3a5c] mb-4">{formatCurrency(avgDeal.overall_avg)}</p>
            <div className="grid grid-cols-2 gap-3">
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

        {income && income.length > 0 && (
          <div className="bg-white rounded-xl border p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold">Поступления</h2>
              <select
                value={incomeMonths}
                onChange={(e) => setIncomeMonths(Number(e.target.value))}
                className="px-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              >
                <option value={3}>3 месяца</option>
                <option value={6}>6 месяцев</option>
                <option value={12}>12 месяцев</option>
              </select>
            </div>
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
      </div>

      {overdueDeals && overdueDeals.length > 0 && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Просроченные сделки</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Клиент</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Менеджер</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Сумма</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Дней</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {overdueDeals.map((d) => (
                  <tr key={d.deal_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">
                      <Link href={`/deals/${d.deal_id}`} className="text-[#1a3a5c] hover:underline">
                        {d.client_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{d.manager_name}</td>
                    <td className="px-4 py-3 font-semibold text-red-600">{formatCurrency(d.deal_total)}</td>
                    <td className="px-4 py-3">{d.days_overdue}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {managerActivity && managerActivity.length > 0 && (
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Активность менеджеров</h2>
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
                  <th className="py-2 pr-4">Менеджер</th>
                  <th className="py-2 pr-4">Действий</th>
                  <th className="py-2 pr-4">Чаще всего</th>
                  <th className="py-2">Последнее</th>
                </tr>
              </thead>
              <tbody>
                {managerActivity.map((u) => (
                  <tr key={u.user_id} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{u.name}</td>
                    <td className="py-2 pr-4">{u.action_count}</td>
                    <td className="py-2 pr-4 text-gray-500">
                      {u.top_action ? (ACTION_LABELS[u.top_action] ?? u.top_action) : "—"}
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

function Kpi({
  label,
  value,
  accent,
  warn,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
  warn?: boolean;
}) {
  return (
    <div
      className={`bg-white rounded-xl border p-4 ${
        accent ? "border-[#1a3a5c]" : warn ? "border-red-200 bg-red-50" : ""
      }`}
    >
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-xl font-bold ${warn ? "text-red-600" : ""}`}>{value}</p>
    </div>
  );
}
