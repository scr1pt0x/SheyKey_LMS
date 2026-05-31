"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { useManagerCash, useAddCashEntry } from "@/hooks/useManager";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import {
  formatCurrency,
  formatDateTime,
  PAYMENT_METHOD_LABELS,
} from "@/lib/utils";
import { Wallet, Plus, Minus, X } from "lucide-react";

const ENTRY_TYPE_LABELS: Record<string, string> = {
  installment: "Рассрочка",
  manual: "Приход",
  expense: "Расход",
};

type CashFormMode = null | "income" | "expense";

export function ManagerCashSection() {
  const [formMode, setFormMode] = useState<CashFormMode>(null);
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("cash");
  const [paidAt, setPaidAt] = useState(new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");

  const { data, isLoading, isError, error, refetch } = useManagerCash({ limit: 15 });
  const addEntry = useAddCashEntry();
  const qc = useQueryClient();

  const closeForm = () => {
    setFormMode(null);
    setAmount("");
    setDescription("");
  };

  const submitEntry = () => {
    if (!formMode) return;
    const parsed = parseFloat(amount.replace(",", "."));
    if (!parsed || parsed <= 0) {
      toast({ title: "Укажите сумму", variant: "destructive" });
      return;
    }
    if (!description.trim()) {
      toast({ title: "Укажите описание", variant: "destructive" });
      return;
    }
    addEntry.mutate(
      {
        amount: String(parsed),
        paid_at: paidAt + "T12:00:00Z",
        method,
        description: description.trim(),
        entry_kind: formMode,
      },
      {
        onSuccess: () => {
          toast({
            title: formMode === "expense" ? "Расход записан" : "Поступление добавлено в кассу",
          });
          closeForm();
          qc.invalidateQueries({ queryKey: ["manager-dashboard"] });
        },
        onError: (err) =>
          toast({
            title: "Ошибка",
            description: getErrorMessage(err),
            variant: "destructive",
          }),
      }
    );
  };

  const isExpense = (type: string) => type === "expense";

  return (
    <div className="bg-white rounded-xl border p-4 space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h2 className="font-semibold text-sm flex items-center gap-2">
          <Wallet size={18} className="text-[#1a3a5c]" />
          Касса
        </h2>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setFormMode(formMode === "income" ? null : "income")}
          >
            {formMode === "income" ? <X size={14} /> : <Plus size={14} />}
            {formMode === "income" ? "Отмена" : "Приход"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-red-700 border-red-200 hover:bg-red-50"
            onClick={() => setFormMode(formMode === "expense" ? null : "expense")}
          >
            {formMode === "expense" ? <X size={14} /> : <Minus size={14} />}
            {formMode === "expense" ? "Отмена" : "Расход"}
          </Button>
        </div>
      </div>

      {data && (
        <div className="grid grid-cols-3 gap-2">
          <div className="bg-[#1a3a5c]/5 rounded-lg p-3 text-center">
            <p className="text-[10px] text-gray-500 uppercase">Остаток сегодня</p>
            <p className="text-sm font-bold text-[#1a3a5c]">{formatCurrency(data.total_today)}</p>
          </div>
          <div className="bg-[#1a3a5c]/5 rounded-lg p-3 text-center">
            <p className="text-[10px] text-gray-500 uppercase">Остаток за месяц</p>
            <p className="text-sm font-bold text-[#1a3a5c]">{formatCurrency(data.total_month)}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-[10px] text-gray-500 uppercase">Остаток всего</p>
            <p className="text-sm font-bold text-gray-700">{formatCurrency(data.total_all_time)}</p>
          </div>
        </div>
      )}

      {formMode && (
        <div
          className={`border rounded-lg p-3 space-y-3 ${
            formMode === "expense" ? "bg-red-50/50 border-red-100" : "bg-gray-50"
          }`}
        >
          <p className="text-xs text-gray-500">
            {formMode === "expense"
              ? "Списание из кассы (сумма не может превышать остаток)."
              : "Поступление не привязано к сделке."}
          </p>
          {formMode === "expense" && data && (
            <p className="text-xs font-medium text-gray-700">
              Доступно в кассе: {formatCurrency(data.total_all_time)}
            </p>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-600 block mb-1">Сумма</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              />
            </div>
            <div>
              <label className="text-xs text-gray-600 block mb-1">Дата</label>
              <input
                type="date"
                value={paidAt}
                onChange={(e) => setPaidAt(e.target.value)}
                className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-600 block mb-1">Способ</label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            >
              {Object.entries(PAYMENT_METHOD_LABELS).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-600 block mb-1">Описание</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={
                formMode === "expense"
                  ? "Например: канцтовары, доставка клиенту"
                  : "Например: прочее поступление"
              }
              className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            />
          </div>
          <Button
            size="sm"
            loading={addEntry.isPending}
            onClick={submitEntry}
            className={`w-full ${formMode === "expense" ? "bg-red-700 hover:bg-red-800" : ""}`}
          >
            {formMode === "expense" ? "Списать из кассы" : "Записать в кассу"}
          </Button>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-6">
          <div className="animate-spin h-6 w-6 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : isError ? (
        <div className="text-sm text-red-600 space-y-2">
          <p>Не удалось загрузить кассу: {getErrorMessage(error)}</p>
          <Button size="sm" variant="outline" onClick={() => refetch()}>
            Повторить
          </Button>
        </div>
      ) : !data?.items.length ? (
        <p className="text-sm text-gray-500">
          Пока нет операций. Платежи по рассрочке появятся после приёма оплаты по сделкам.
        </p>
      ) : (
        <ul className="space-y-2 max-h-64 overflow-y-auto">
          {data.items.map((item) => (
            <li
              key={item.id}
              className="flex items-start justify-between gap-2 text-sm border-b border-gray-100 pb-2 last:border-0"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge
                    className={
                      item.entry_type === "installment"
                        ? "bg-green-100 text-green-800"
                        : item.entry_type === "expense"
                          ? "bg-red-100 text-red-800"
                          : "bg-blue-100 text-blue-800"
                    }
                  >
                    {ENTRY_TYPE_LABELS[item.entry_type]}
                  </Badge>
                  <span className="text-xs text-gray-400">
                    {PAYMENT_METHOD_LABELS[item.method] ?? item.method}
                  </span>
                </div>
                {item.deal_id ? (
                  <Link
                    href={`/deals/${item.deal_id}`}
                    className="text-[#1a3a5c] hover:underline block truncate mt-0.5"
                  >
                    {item.description}
                  </Link>
                ) : (
                  <p className="mt-0.5 break-words">{item.description}</p>
                )}
                <p className="text-xs text-gray-400 mt-0.5">{formatDateTime(item.paid_at)}</p>
              </div>
              <span
                className={`font-semibold whitespace-nowrap ${
                  isExpense(item.entry_type) ? "text-red-600" : "text-[#1a3a5c]"
                }`}
              >
                {isExpense(item.entry_type) ? "−" : "+"}
                {formatCurrency(item.amount)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
