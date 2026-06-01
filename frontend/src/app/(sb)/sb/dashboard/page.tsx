"use client";

import { useSbDashboard, useSbTodayWork, type SbTodayWorkItem } from "@/hooks/useSb";
import {
  formatCurrency,
  formatDateTime,
  SB_STAGE_EMPTY_HINT,
  sbStageBannerTitle,
} from "@/lib/utils";
import Link from "next/link";
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
  const { data: todayWork } = useSbTodayWork();

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

      {data.assigned_collection_stage != null && (
        <div className="bg-white rounded-xl border p-4">
          <h2 className="font-semibold text-sm flex items-center gap-2 mb-2">
            <AlertTriangle size={18} className="text-amber-600" />
            {sbStageBannerTitle(data.assigned_collection_stage)}
          </h2>
          {!data.stage_open_cases?.length ? (
            <p className="text-sm text-gray-500">
              {SB_STAGE_EMPTY_HINT[data.assigned_collection_stage] ??
                "На вашем этапе дел пока нет — они появятся при эскалации просрочки."}
            </p>
          ) : (
            <ul className="space-y-2">
              {data.stage_open_cases.map((c) => (
                <li key={c.case_id}>
                  <Link
                    href={`/sb/cases/${c.case_id}`}
                    className="flex justify-between items-center hover:bg-gray-50 rounded-lg p-2 -mx-2"
                  >
                    <span className="text-sm">
                      {c.client_name ?? "Клиент"} · {c.days_overdue} дн. · {c.overdue_installments_count} плат.
                    </span>
                    <span className="text-sm text-red-600 font-semibold">{formatCurrency(c.total_debt)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link href="/sb/cases" className="text-xs text-[#1a3a5c] hover:underline mt-2 inline-block">
            Все мои дела →
          </Link>
        </div>
      )}

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

      {todayWork && (
        <div className="space-y-4">
          <h2 className="font-semibold text-lg">Работа на сегодня</h2>
          <WorkSection
            title="Красная зона"
            items={todayWork.red_zone_cases}
            emptyText="Нет дел в красной зоне"
            variant="red"
          />
          <WorkSection
            title="Обещания на сегодня"
            items={todayWork.promises_today}
            emptyText="Нет обещаний на сегодня"
          />
          <WorkSection
            title="Просроченные обещания"
            items={todayWork.promises_overdue}
            emptyText="Нет просроченных обещаний"
            variant="red"
          />
        </div>
      )}

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
            <Tooltip
              formatter={(value: number) => [`${value} дел`, ""]}
              labelStyle={{ fontWeight: 600 }}
              contentStyle={{ borderRadius: "8px", fontSize: "13px" }}
              cursor={{ fill: "rgba(0,0,0,0.05)" }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} name="Дел">
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

function WorkSection({
  title,
  items,
  emptyText,
  variant,
}: {
  title: string;
  items: SbTodayWorkItem[];
  emptyText: string;
  variant?: "red";
}) {
  if (items.length === 0) {
    return (
      <div className="bg-white rounded-xl border p-4">
        <h3 className="font-medium text-sm mb-1">{title}</h3>
        <p className="text-sm text-gray-500">{emptyText}</p>
      </div>
    );
  }
  return (
    <div className={`rounded-xl border p-4 ${variant === "red" ? "bg-red-50 border-red-200" : "bg-white"}`}>
      <h3 className="font-medium text-sm mb-3">{title}</h3>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item.case_id + (item.promise_id ?? "")}>
            <Link href={`/sb/cases/${item.case_id}`} className="block hover:bg-black/5 rounded-lg p-2 -mx-2">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-red-600">{formatCurrency(item.total_debt)}</span>
                <span className="text-gray-500">{item.days_overdue} дн.</span>
              </div>
              {item.promised_date && (
                <p className="text-xs text-gray-600 mt-0.5">
                  Обещание: {item.promised_date} — {formatCurrency(item.promised_amount ?? 0)}
                </p>
              )}
              {item.last_contact_at && (
                <p className="text-xs text-gray-400">Контакт: {formatDateTime(item.last_contact_at)}</p>
              )}
            </Link>
          </li>
        ))}
      </ul>
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
