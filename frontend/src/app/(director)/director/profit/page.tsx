"use client";

import { useState } from "react";
import { useProfitPeriods, useCalculatePeriod, useApprovePeriod, type ProfitPeriod } from "@/hooks/useProfit";
import { profitCalculateSchema } from "@/lib/schemas/profit";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, formatDate } from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { TrendingUp, ChevronDown, ChevronUp, CheckCircle, Calculator } from "lucide-react";

export default function ProfitPage() {
  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);

  const [periodStart, setPeriodStart] = useState(firstDay);
  const [periodEnd, setPeriodEnd] = useState(lastDay);
  const [activePeriod, setActivePeriod] = useState<ProfitPeriod | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: periods, isLoading } = useProfitPeriods();
  const calculate = useCalculatePeriod();
  const approve = useApprovePeriod();

  function handleCalculate() {
    const parsed = profitCalculateSchema.safeParse({ period_start: periodStart, period_end: periodEnd });
    if (!parsed.success) {
      toast({ title: "Проверьте период", description: parsed.error.errors[0]?.message, variant: "destructive" });
      return;
    }
    calculate.mutate(parsed.data, {
      onSuccess: (period) => {
        setActivePeriod(period);
        toast({ title: "Расчёт выполнен" });
      },
      onError: (err) => toast({ title: "Ошибка расчёта", description: getErrorMessage(err), variant: "destructive" }),
    });
  }

  function handleApprove(periodId: string) {
    approve.mutate(periodId, {
      onSuccess: () => {
        toast({ title: "Распределение утверждено" });
        setActivePeriod(null);
      },
      onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
    });
  }

  const displayPeriod = activePeriod ?? null;

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-2">
        <TrendingUp size={22} className="text-[#1a3a5c]" />
        <h1 className="text-xl font-bold">Распределение прибыли</h1>
      </div>

      {/* Period selector */}
      <div className="bg-white rounded-xl border p-5 space-y-4">
        <h2 className="font-semibold">Выберите период</h2>
        <div className="flex gap-3 flex-wrap items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">С</label>
            <input
              type="date"
              value={periodStart}
              onChange={(e) => setPeriodStart(e.target.value)}
              className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">По</label>
            <input
              type="date"
              value={periodEnd}
              onChange={(e) => setPeriodEnd(e.target.value)}
              className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            />
          </div>
          <Button loading={calculate.isPending} onClick={handleCalculate}>
            <Calculator size={16} /> Рассчитать
          </Button>
        </div>
      </div>

      {/* Visual formula for active calculation */}
      {displayPeriod && (
        <ProfitFormula
          period={displayPeriod}
          onApprove={() => handleApprove(displayPeriod.id)}
          approving={approve.isPending}
        />
      )}

      {/* History */}
      {!isLoading && periods && periods.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-semibold text-gray-700">История периодов</h2>
          {periods.map((p) => (
            <div key={p.id} className="bg-white rounded-xl border overflow-hidden">
              <button
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
              >
                <div className="flex items-center gap-3">
                  <Badge className={p.status === "approved" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}>
                    {p.status === "approved" ? "Утверждён" : "Черновик"}
                  </Badge>
                  <span className="font-medium text-sm">
                    {formatDate(p.period_start)} — {formatDate(p.period_end)}
                  </span>
                  <span className="text-gray-500 text-sm hidden sm:inline">
                    Выручка: {formatCurrency(p.gross_revenue)}
                  </span>
                </div>
                {expandedId === p.id ? <ChevronUp size={18} className="text-gray-400" /> : <ChevronDown size={18} className="text-gray-400" />}
              </button>
              {expandedId === p.id && (
                <div className="border-t">
                  <ProfitFormula
                    period={p}
                    onApprove={p.status === "draft" ? () => handleApprove(p.id) : undefined}
                    approving={approve.isPending}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


function ProfitFormula({
  period,
  onApprove,
  approving,
}: {
  period: ProfitPeriod;
  onApprove?: () => void;
  approving?: boolean;
}) {
  return (
    <div className="bg-white rounded-xl border overflow-hidden">
      <div className="p-5 space-y-0">

        {/* Incoming */}
        <FormulaRow
          label="Входящие платежи от клиентов"
          value={formatCurrency(period.gross_revenue)}
          type="income"
        />

        {/* Expenses */}
        <FormulaRow
          label={`Расходы периода`}
          value={`− ${formatCurrency(period.total_expenses)}`}
          type="minus"
        />

        {/* Net company */}
        <FormulaRow
          label="Чистая прибыль компании"
          value={formatCurrency(period.gross_revenue - period.total_expenses)}
          type="result"
        />

        {/* Manager bonus */}
        <FormulaRow
          label={`Бонусы менеджерам (${period.manager_bonus_pct}%)`}
          value={`− ${formatCurrency(period.manager_bonus_amount)}`}
          type="minus"
        />

        {/* Distributable */}
        <FormulaRow
          label="К распределению между инвесторами"
          value={formatCurrency(period.net_distributable)}
          type="result"
          highlight
        />

        {/* Investors */}
        {period.distributions.length > 0 && (
          <div className="mt-1 mb-1 ml-4 space-y-0">
            {period.distributions.map((d) => (
              <FormulaRow
                key={d.investor_id}
                label={`${d.investor_name} (${d.share_pct}%)`}
                value={formatCurrency(d.amount)}
                type="investor"
              />
            ))}
          </div>
        )}

        {/* Partner remainder */}
        {period.partner_remainder > 0 && (
          <FormulaRow
            label={`Остаток партнёрам (${(100 - period.distributions.reduce((s, d) => s + d.share_pct, 0)).toFixed(2)}%)`}
            value={formatCurrency(period.partner_remainder)}
            type="partner"
          />
        )}

        {/* Actions */}
        <div className="pt-4 flex gap-3">
          {onApprove && period.status === "draft" && (
            <Button loading={approving} onClick={onApprove}>
              <CheckCircle size={16} /> Утвердить распределение
            </Button>
          )}
          {period.status === "approved" && (
            <div className="flex items-center gap-2 text-green-700 text-sm font-medium">
              <CheckCircle size={18} />
              Утверждено {period.approved_at ? formatDate(period.approved_at) : ""}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


function FormulaRow({
  label,
  value,
  type,
  highlight,
}: {
  label: string;
  value: string;
  type: "income" | "minus" | "result" | "investor" | "partner";
  highlight?: boolean;
}) {
  const rowStyles: Record<string, string> = {
    income: "py-2.5 border-b border-gray-100",
    minus: "py-2 border-b border-gray-100",
    result: "py-3 border-b-2 border-gray-200 font-semibold",
    investor: "py-2 border-b border-gray-50",
    partner: "py-2.5 border-t border-gray-200 font-semibold",
  };

  const valueStyles: Record<string, string> = {
    income: "font-semibold text-gray-800",
    minus: "text-red-600",
    result: highlight ? "text-[#1a3a5c] text-xl font-bold" : "font-semibold text-gray-800",
    investor: "font-medium text-green-700",
    partner: "font-semibold text-gray-700",
  };

  const labelStyles: Record<string, string> = {
    income: "text-gray-700",
    minus: "text-gray-500 text-sm",
    result: highlight ? "text-[#1a3a5c] font-semibold" : "text-gray-700",
    investor: "text-gray-600 text-sm",
    partner: "text-gray-600",
  };

  return (
    <div className={`flex items-center justify-between ${rowStyles[type]} ${highlight ? "bg-blue-50 -mx-5 px-5" : ""}`}>
      <span className={labelStyles[type]}>{label}</span>
      <span className={valueStyles[type]}>{value}</span>
    </div>
  );
}
