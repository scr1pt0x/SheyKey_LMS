"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { formatCurrency, formatDate, formatDateTime, PAYMENT_METHOD_LABELS } from "@/lib/utils";

export interface DealScheduleLine {
  id: string;
  installment_number: number;
  due_date: string;
  amount: string;
  paid_amount: string;
  status: string;
}

interface DealPaymentPanelProps {
  dealId: string;
  schedules: DealScheduleLine[];
  /** When false, only payment history is shown */
  canRecord?: boolean;
  onRecorded?: () => void;
}

export function DealPaymentPanel({
  dealId,
  schedules,
  canRecord = true,
  onRecorded,
}: DealPaymentPanelProps) {
  const qc = useQueryClient();
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [paidAt, setPaidAt] = useState(new Date().toISOString().slice(0, 10));

  const pendingSchedules = schedules.filter((s) => s.status !== "paid");
  const totalScheduleRemaining = pendingSchedules.reduce(
    (sum, s) => sum + Math.max(0, parseFloat(s.amount) - parseFloat(s.paid_amount)),
    0
  );

  const { data: dealPayments } = useQuery({
    queryKey: ["deal-payments", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/api/payments/deal/${dealId}`, { params: { limit: 50 } });
      return data as {
        items: { id: string; amount: string; paid_at: string; method: string; created_at: string }[];
      };
    },
    enabled: !!dealId,
  });

  const recordPayment = useMutation({
    mutationFn: () =>
      api.post("/api/payments/allocate", {
        deal_id: dealId,
        amount: paymentAmount,
        paid_at: paidAt + "T00:00:00Z",
        method: paymentMethod,
      }),
    onSuccess: (res) => {
      const parts = (res.data as { payments: unknown[] }).payments.length;
      toast({
        title: "Платёж зафиксирован",
        description: parts > 1 ? `Распределено по ${parts} строкам графика` : undefined,
      });
      setPaymentAmount("");
      qc.invalidateQueries({ queryKey: ["deal-payments", dealId] });
      qc.invalidateQueries({ queryKey: ["deals", dealId] });
      qc.invalidateQueries({ queryKey: ["manager-dashboard"] });
      qc.invalidateQueries({ queryKey: ["manager-stats"] });
      qc.invalidateQueries({ queryKey: ["manager-cash"] });
      onRecorded?.();
    },
    onError: (err) =>
      toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  return (
    <div className="space-y-4">
      {canRecord && pendingSchedules.length > 0 ? (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <div>
            <h2 className="font-semibold">Зафиксировать платёж</h2>
            <p className="text-sm text-gray-500 mt-1">
              Сумма автоматически спишется с ближайших неоплаченных строк графика.
              Остаток по графику: {formatCurrency(totalScheduleRemaining)}
            </p>
          </div>
          <ul className="text-xs text-gray-600 space-y-1 bg-gray-50 rounded-lg p-3">
            {pendingSchedules.map((s) => {
              const remaining = parseFloat(s.amount) - parseFloat(s.paid_amount);
              const isOverdue =
                s.status === "overdue" ||
                (s.status !== "paid" &&
                  new Date(s.due_date) < new Date(new Date().toDateString()));
              return (
                <li key={s.id} className={isOverdue ? "text-red-700 font-medium" : undefined}>
                  №{s.installment_number} · {formatDate(s.due_date)}
                  {isOverdue ? " · просрочка" : ""} · остаток {formatCurrency(remaining)}
                </li>
              );
            })}
          </ul>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Сумма (₽) *</label>
              <input
                type="number"
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                placeholder="Свободная сумма"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Дата платежа *</label>
              <input
                type="date"
                value={paidAt}
                onChange={(e) => setPaidAt(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium mb-1">Способ оплаты *</label>
              <select
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              >
                {Object.entries(PAYMENT_METHOD_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <Button
            size="sm"
            loading={recordPayment.isPending}
            disabled={!paymentAmount || parseFloat(paymentAmount) <= 0}
            onClick={() => recordPayment.mutate()}
          >
            Зафиксировать платёж
          </Button>
        </div>
      ) : canRecord ? (
        <p className="text-sm text-gray-500 bg-white rounded-xl border p-4">
          Нет неоплаченных строк графика.
        </p>
      ) : null}

      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="p-4 border-b">
          <h3 className="font-semibold text-sm">История платежей</h3>
        </div>
        {dealPayments?.items.length ? (
          <ul className="divide-y">
            {dealPayments.items.map((p) => (
              <li key={p.id} className="px-4 py-3 flex items-center justify-between text-sm">
                <div>
                  <p className="font-medium">{formatCurrency(p.amount)}</p>
                  <p className="text-gray-500 text-xs">
                    {formatDate(p.paid_at)} · {PAYMENT_METHOD_LABELS[p.method] ?? p.method}
                  </p>
                </div>
                <span className="text-xs text-gray-400">{formatDateTime(p.created_at)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="p-4 text-sm text-gray-500 text-center">Платежей пока нет</p>
        )}
      </div>
    </div>
  );
}
