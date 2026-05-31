"use client";

import { useDirectorDashboard } from "@/hooks/useDirector";
import { formatCurrency } from "@/lib/utils";

export default function DirectorDashboardPage() {
  const { data: dashboard, isLoading } = useDirectorDashboard();

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

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Общий портфель" value={formatCurrency(dashboard.total_portfolio)} accent />
        <KpiCard label="Активные сделки" value={dashboard.active_deals} />
        <KpiCard label="Просрочено" value={`${dashboard.overdue_pct}%`} warn={dashboard.overdue_pct > 10} />
        <KpiCard label="Новых в месяц" value={dashboard.new_deals_month} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <CashCard label="Поступления сегодня" value={dashboard.cash_flow_today} />
        <CashCard label="Поступления — 7 дней" subtitle="факт, за последние 7 дней" value={dashboard.cash_flow_week} />
        <CashCard label="Поступления за месяц" subtitle="факт, с 1-го числа" value={dashboard.cash_flow_month} />
      </div>

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
