"use client";

import Link from "next/link";
import { useManagerDashboard, useManagerStats } from "@/hooks/useManager";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  formatCurrency,
  formatDate,
  DEAL_TYPE_LABELS,
  DEAL_STATUS_LABELS,
  DEAL_STATUS_COLORS,
} from "@/lib/utils";
import { ManagerCashSection } from "@/components/features/manager/ManagerCashSection";
import { Home, Plus, Users, AlertTriangle, CreditCard } from "lucide-react";

export default function ManagerDashboardPage() {
  const { data, isLoading } = useManagerDashboard();
  const { data: stats } = useManagerStats();

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Home size={22} className="text-[#1a3a5c]" /> Мой портфель
        </h1>
        <div className="flex gap-2">
          <Link href="/clients/new">
            <Button size="sm" variant="outline"><Users size={16} /> Клиент</Button>
          </Link>
          <Link href="/deals/new">
            <Button size="sm"><Plus size={16} /> Сделка</Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Активные сделки" value={data.active_deals} />
        <Kpi label="Просрочено" value={data.overdue_deals} warn={data.overdue_deals > 0} />
        <Kpi label="На согласовании" value={data.pending_deals} />
        <Kpi label="Черновики" value={data.draft_deals} />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <CashKpi label="Портфель (активные)" value={data.portfolio_active_total} />
        <CashKpi label="Поступления сегодня" value={data.payments_today} />
        <CashKpi label="Поступления за месяц" value={data.payments_month} />
      </div>

      <ManagerCashSection />

      {stats && (
        <div className="bg-white rounded-xl border p-4 text-sm text-gray-600">
          <p>
            За месяц: сделок создано <strong>{stats.deals_created}</strong>, принято платежей{" "}
            <strong>{formatCurrency(stats.payments_collected)}</strong>.
          </p>
          <p className="text-xs text-gray-400 mt-1">{stats.bonus_note}</p>
        </div>
      )}

      {data.clients_kyc_pending > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <Link href="/clients?kyc=pending" className="text-sm font-medium text-yellow-800 hover:underline">
            KYC на проверке: {data.clients_kyc_pending} клиент(ов) →
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Section title="Моя просрочка" icon={<AlertTriangle size={18} className="text-red-500" />}>
          {data.overdue_deals_list.length === 0 ? (
            <p className="text-sm text-gray-500">Просроченных сделок нет</p>
          ) : (
            <ul className="space-y-2">
              {data.overdue_deals_list.map((d) => (
                <li key={d.id}>
                  <Link href={`/deals/${d.id}`} className="flex justify-between items-center hover:bg-gray-50 rounded-lg p-2 -mx-2">
                    <span className="text-sm font-medium">{DEAL_TYPE_LABELS[d.type]}</span>
                    <span className="text-sm text-red-600 font-semibold">{formatCurrency(d.total)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {data.overdue_deals > 0 && (
            <Link href="/deals?status=overdue" className="text-xs text-[#1a3a5c] hover:underline mt-2 inline-block">
              Все просроченные →
            </Link>
          )}
        </Section>

        <Section title="На согласовании">
          {data.pending_deals_list.length === 0 ? (
            <p className="text-sm text-gray-500">Нет сделок в ожидании</p>
          ) : (
            <ul className="space-y-2">
              {data.pending_deals_list.map((d) => (
                <li key={d.id}>
                  <Link href={`/deals/${d.id}`} className="flex justify-between items-center hover:bg-gray-50 rounded-lg p-2 -mx-2">
                    <Badge className={DEAL_STATUS_COLORS[d.status]}>{DEAL_STATUS_LABELS[d.status]}</Badge>
                    <span className="text-sm font-medium">{formatCurrency(d.total)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Платежи сегодня по графику" icon={<CreditCard size={18} />}>
          {data.schedules_today.length === 0 ? (
            <p className="text-sm text-gray-500">Нет ожидаемых платежей на сегодня</p>
          ) : (
            <ul className="space-y-2">
              {data.schedules_today.map((s) => (
                <li key={s.schedule_id}>
                  <Link href={`/deals/${s.deal_id}`} className="flex justify-between text-sm hover:bg-gray-50 rounded-lg p-2 -mx-2">
                    <span>{formatDate(s.due_date)}</span>
                    <span className="font-medium">{formatCurrency(s.amount)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <Link href="/calendar" className="text-xs text-[#1a3a5c] hover:underline mt-2 inline-block">
            Календарь →
          </Link>
        </Section>

        <Section title="Платежи на 7 дней">
          {data.schedules_week.length === 0 ? (
            <p className="text-sm text-gray-500">Нет платежей на ближайшую неделю</p>
          ) : (
            <ul className="space-y-2 max-h-48 overflow-y-auto">
              {data.schedules_week.map((s) => (
                <li key={s.schedule_id}>
                  <Link href={`/deals/${s.deal_id}`} className="flex justify-between text-sm hover:bg-gray-50 rounded-lg p-2 -mx-2">
                    <span>{formatDate(s.due_date)}</span>
                    <span className="font-medium">{formatCurrency(s.amount)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>
    </div>
  );
}

function Kpi({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className={`bg-white rounded-xl border p-4 ${warn ? "border-red-200 bg-red-50" : ""}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-2xl font-bold ${warn ? "text-red-600" : ""}`}>{value}</p>
    </div>
  );
}

function CashKpi({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-[#1a3a5c] rounded-xl p-4 text-white">
      <p className="text-xs text-white/70">{label}</p>
      <p className="text-lg font-bold">{formatCurrency(value)}</p>
    </div>
  );
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl border p-4">
      <h2 className="font-semibold text-sm mb-3 flex items-center gap-2">
        {icon}
        {title}
      </h2>
      {children}
    </div>
  );
}
