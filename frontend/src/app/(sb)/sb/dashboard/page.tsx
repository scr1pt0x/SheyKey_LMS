"use client";

import { useSbDashboard } from "@/hooks/useSb";
import { formatCurrency } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { AlertTriangle, CheckCircle, Clock, TrendingUp } from "lucide-react";

export default function SbDashboardPage() {
  const { data, isLoading } = useSbDashboard();

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
      </div>
    );
  }
  if (!data) return null;

  const caseChartData = [
    { name: "Новые", value: data.my_cases_new, fill: "#ef4444" },
    { name: "В работе", value: data.my_cases_in_progress, fill: "#f59e0b" },
    { name: "Договорились", value: data.my_cases_agreed, fill: "#3b82f6" },
    { name: "Закрыты", value: data.my_cases_closed, fill: "#22c55e" },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Мой дашборд — Служба Безопасности</h1>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          icon={<AlertTriangle size={20} className="text-red-500" />}
          label="Новые дела"
          value={data.my_cases_new}
          highlight={data.my_cases_new > 0}
        />
        <KpiCard
          icon={<Clock size={20} className="text-yellow-500" />}
          label="В работе"
          value={data.my_cases_in_progress}
        />
        <KpiCard
          icon={<TrendingUp size={20} className="text-[#1a3a5c]" />}
          label="Обещания сегодня"
          value={data.promises_today}
          highlight={data.promises_today > 0}
        />
        <KpiCard
          icon={<CheckCircle size={20} className="text-green-500" />}
          label="Взыскано в месяц"
          value={formatCurrency(data.recovered_this_month)}
        />
      </div>

      {/* Red zone warning */}
      {data.red_zone_cases > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <AlertTriangle size={20} className="text-red-600 shrink-0" />
          <p className="text-red-700 font-medium">
            Красная зона: {data.red_zone_cases} дел без контакта более установленного срока
          </p>
        </div>
      )}

      {/* Cases by status chart */}
      <div className="bg-white rounded-xl border p-5">
        <h2 className="font-semibold mb-4">Мои дела по статусам</h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={caseChartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {caseChartData.map((entry, index) => (
                <rect key={index} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Promises */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border p-5">
          <p className="text-sm text-gray-500 mb-1">Обещания платежей — сегодня</p>
          <p className="text-3xl font-bold text-[#1a3a5c]">{data.promises_today}</p>
        </div>
        <div className="bg-white rounded-xl border p-5">
          <p className="text-sm text-gray-500 mb-1">Обещания платежей — неделя</p>
          <p className="text-3xl font-bold text-[#1a3a5c]">{data.promises_this_week}</p>
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  icon,
  label,
  value,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <div
      className={`bg-white rounded-xl border p-4 ${
        highlight ? "border-red-200 bg-red-50" : ""
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs text-gray-500">{label}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
