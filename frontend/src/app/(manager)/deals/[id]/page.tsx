"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useDeal, useSubmitDeal } from "@/hooks/useDeals";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DocumentsSection } from "@/components/features/shared/DocumentsSection";
import {
  formatDate,
  formatCurrency,
  DEAL_TYPE_LABELS,
  DEAL_STATUS_LABELS,
  DEAL_STATUS_COLORS,
  PAYMENT_METHOD_LABELS,
} from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { ArrowLeft, Download, CreditCard } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";

export default function DealDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: deal, isLoading } = useDeal(id);
  const submitDeal = useSubmitDeal();
  const qc = useQueryClient();
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const [scheduleId, setScheduleId] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("cash");
  const [paidAt, setPaidAt] = useState(new Date().toISOString().slice(0, 10));

  const recordPayment = useMutation({
    mutationFn: () =>
      api.post("/api/payments", {
        schedule_id: scheduleId,
        amount,
        paid_at: paidAt + "T00:00:00Z",
        method,
      }),
    onSuccess: () => {
      toast({ title: "Платёж зафиксирован" });
      setShowPaymentForm(false);
      qc.invalidateQueries({ queryKey: ["deals", id] });
    },
    onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  if (isLoading) {
    return <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" /></div>;
  }
  if (!deal) return <p className="text-center py-8">Сделка не найдена</p>;

  const pendingSchedules = deal.payment_schedules.filter((s) => s.status !== "paid");

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link href="/deals">
          <Button variant="ghost" size="icon"><ArrowLeft size={20} /></Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold">{DEAL_TYPE_LABELS[deal.type]}</h1>
          <Badge className={DEAL_STATUS_COLORS[deal.status]}>{DEAL_STATUS_LABELS[deal.status]}</Badge>
        </div>
        <div className="flex gap-2">
          {deal.status === "draft" && (
            <Button
              size="sm"
              loading={submitDeal.isPending}
              onClick={() =>
                submitDeal.mutate(id, {
                  onSuccess: () => toast({ title: "Сделка отправлена на согласование" }),
                  onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
                })
              }
            >
              На согласование
            </Button>
          )}
          {deal.status === "active" && (
            <Button size="sm" variant="outline" onClick={() => setShowPaymentForm(!showPaymentForm)}>
              <CreditCard size={16} /> Платёж
            </Button>
          )}
          <a href={`/api/documents/generate/schedule/${id}`} target="_blank" rel="noreferrer">
            <Button size="sm" variant="outline"><Download size={16} /> График PDF</Button>
          </a>
          <a href={`/api/documents/generate/contract/${id}`} target="_blank" rel="noreferrer">
            <Button size="sm" variant="outline"><Download size={16} /> Договор</Button>
          </a>
        </div>
      </div>

      {/* Payment form */}
      {showPaymentForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h2 className="font-semibold">Зафиксировать платёж</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Строка графика *</label>
              <select
                value={scheduleId}
                onChange={(e) => setScheduleId(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              >
                <option value="">Выберите...</option>
                {pendingSchedules.map((s) => (
                  <option key={s.id} value={s.id}>
                    #{s.installment_number} — {formatDate(s.due_date)} — {formatCurrency(s.amount)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Сумма (₽) *</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
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
            <div>
              <label className="block text-sm font-medium mb-1">Способ оплаты *</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              >
                {Object.entries(PAYMENT_METHOD_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="sm" loading={recordPayment.isPending} onClick={() => recordPayment.mutate()}>
              Зафиксировать
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowPaymentForm(false)}>Отмена</Button>
          </div>
        </div>
      )}

      {/* Deal info */}
      <div className="bg-white rounded-xl border p-5 grid grid-cols-2 sm:grid-cols-3 gap-4">
        <Info label="Основная сумма">{formatCurrency(deal.principal)}</Info>
        <Info label="Наценка">{formatCurrency(deal.markup)}</Info>
        <Info label="Итого к выплате"><span className="text-lg font-bold">{formatCurrency(deal.total)}</span></Info>
        <Info label="Срок">{deal.duration_months} мес.</Info>
        <Info label="Дата начала">{deal.start_date ? formatDate(deal.start_date) : "—"}</Info>
        <Info label="Дата окончания">{deal.end_date ? formatDate(deal.end_date) : "—"}</Info>
        {deal.rejection_comment && (
          <Info label="Причина отклонения" className="col-span-full">
            <p className="text-red-600">{deal.rejection_comment}</p>
          </Info>
        )}
      </div>

      {/* Documents */}
      <div className="bg-white rounded-xl border p-5">
        <h2 className="font-semibold mb-4">Документы</h2>
        <DocumentsSection
          entityType="deal"
          entityId={id}
          availableDocTypes={["contract", "collateral", "photo", "receipt", "other"]}
        />
      </div>

      {/* Payment schedule */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="p-4 border-b">
          <h2 className="font-semibold">График платежей</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">№</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Дата</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Сумма</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 hidden sm:table-cell">Оплачено</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 hidden sm:table-cell">Остаток</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Статус</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {deal.payment_schedules.map((s) => {
                const remaining = parseFloat(s.amount) - parseFloat(s.paid_amount);
                const statusColors: Record<string, string> = {
                  pending: "bg-yellow-100 text-yellow-700",
                  paid: "bg-green-100 text-green-800",
                  overdue: "bg-red-100 text-red-800",
                  partial: "bg-orange-100 text-orange-700",
                };
                const statusLabels: Record<string, string> = {
                  pending: "Ожидается",
                  paid: "Оплачен",
                  overdue: "Просрочен",
                  partial: "Частично",
                };
                const typeLabels: Record<string, string> = {
                  principal: "Основной",
                  rent: "Аренда",
                  buyout: "Выкуп",
                };
                return (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{s.installment_number}</td>
                    <td className="px-4 py-3">{formatDate(s.due_date)}</td>
                    <td className="px-4 py-3 font-medium">{formatCurrency(s.amount)}</td>
                    <td className="px-4 py-3 hidden sm:table-cell text-green-700">{formatCurrency(s.paid_amount)}</td>
                    <td className="px-4 py-3 hidden sm:table-cell text-gray-600">{formatCurrency(remaining)}</td>
                    <td className="px-4 py-3">
                      <Badge className={statusColors[s.status]}>{statusLabels[s.status]}</Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Info({ label, children, className }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={className}>
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <div className="font-medium">{children}</div>
    </div>
  );
}
