"use client";

import {
  useDirectorDashboard,
  usePortfolioByType,
  useIssuanceDynamics,
} from "@/hooks/useDirector";
import { formatCurrency, DEAL_TYPE_LABELS } from "@/lib/utils";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const PIE_COLORS = ["#1a3a5c", "#2563eb", "#10b981", "#f59e0b"];

export default function DirectorDashboardPage() {
  const { data: dashboard, isLoading } = useDirectorDashboard();
  const { data: portfolio } = usePortfolioByType();
  const { data: dynamics } = useIssuanceDynamics(12);

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
      </div>
    );
  }
  if (!dashboard) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Главный дашборд</h1>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Общий портфель" value={formatCurrency(dashboard.total_portfolio)} accent />
        <KpiCard label="Активные сделки" value={dashboard.active_deals} />
        <KpiCard label="Просрочено" value={`${dashboard.overdue_pct}%`} warn={dashboard.overdue_pct > 10} />
        <KpiCard label="Новых в месяц" value={dashboard.new_deals_month} />
      </div>

      {/* Cash flow */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <CashCard label="Поступления сегодня" value={dashboard.cash_flow_today} />
        <CashCard label="Поступления — 7 дней" subtitle="факт, за последние 7 дней" value={dashboard.cash_flow_week} />
        <CashCard label="Поступления за месяц" subtitle="факт, с 1-го числа" value={dashboard.cash_flow_month} />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Issuance dynamics */}
        {dynamics && dynamics.length > 0 && (
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold mb-4">Динамика выдач</h2>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={dynamics} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
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
                  fill="url(#colorTotal)"
                  name="Объём"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Portfolio by type */}
        {portfolio && portfolio.length > 0 && (
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold mb-4">Портфель по типам</h2>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={portfolio}
                  dataKey="total_amount"
                  nameKey="type"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ type, pct }: { type: string; pct: number }) =>
                    `${DEAL_TYPE_LABELS[type] ?? type} ${pct}%`
                  }
                >
                  {portfolio.map((_: unknown, index: number) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Income */}
      <div className="bg-white rounded-xl border p-5">
        <p className="text-sm text-gray-500">Доход (фактические поступления) за текущий месяц</p>
        <p className="text-3xl font-bold text-green-600 mt-1">
          {formatCurrency(dashboard.income_month)}
        </p>
      </div>
    </div>
  );
}

function KpiCard({
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
      <p className={`text-2xl font-bold ${warn ? "text-red-600" : ""}`}>{value}</p>
    </div>
  );
}

function CashCard({
  label,
  value,
  subtitle,
}: {
  label: string;
  value: number | string;
  subtitle?: string;
}) {
  return (
    <div className="bg-[#1a3a5c] rounded-xl p-4 text-white">
      <p className="text-xs text-white/70 mb-1">{label}</p>
      {subtitle ? <p className="text-[10px] text-white/50 mb-1">{subtitle}</p> : null}
      <p className="text-xl font-bold">{formatCurrency(value)}</p>
    </div>
  );
}
