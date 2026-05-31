"use client";

import { useState } from "react";
import { useSbStats } from "@/hooks/useSb";
import { formatCurrency } from "@/lib/utils";
import { BarChart2 } from "lucide-react";

export default function SbStatsPage() {
  const today = new Date();
  const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
    .toISOString()
    .slice(0, 10);
  const todayStr = today.toISOString().slice(0, 10);
  const [dateFrom, setDateFrom] = useState(monthStart);
  const [dateTo, setDateTo] = useState(todayStr);

  const { data, isLoading } = useSbStats(dateFrom, dateTo);

  return (
    <div className="space-y-5 w-full">
      <h1 className="text-xl font-bold flex items-center gap-2">
        <BarChart2 size={22} className="text-[#1a3a5c]" /> Моя работа
      </h1>

      <div className="bg-white rounded-xl border p-4 flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">С</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2 text-sm border rounded-lg"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">По</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2 text-sm border rounded-lg"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : data ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <StatCard label="Закрыто дел" value={String(data.cases_closed)} />
          <StatCard
            label="Взыскано платежей"
            value={formatCurrency(data.promises_fulfilled_amount)}
          />
          {data.avg_days_overdue_closed != null && (
            <StatCard
              label="Средняя просрочка (закрытые)"
              value={`${Math.round(data.avg_days_overdue_closed)} дн.`}
            />
          )}
        </div>
      ) : null}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-xl border p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-[#1a3a5c] mt-1">{value}</p>
    </div>
  );
}
