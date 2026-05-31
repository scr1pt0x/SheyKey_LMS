"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { useDeals } from "@/hooks/useDeals";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { RecordPaymentDialog } from "@/components/features/shared/RecordPaymentDialog";
import {
  formatDate,
  formatCurrency,
  DEAL_STATUS_LABELS,
  DEAL_STATUS_COLORS,
  DEAL_TYPE_LABELS,
} from "@/lib/utils";
import { Plus, CreditCard } from "lucide-react";

const LIMIT = 20;
const PAYABLE_STATUSES = new Set(["active", "overdue"]);

export default function DealsPage() {
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [paymentDealId, setPaymentDealId] = useState<string | null>(null);
  const [paymentClientName, setPaymentClientName] = useState<string | null>(null);

  useEffect(() => {
    const s = searchParams.get("status");
    if (s) setStatus(s);
  }, [searchParams]);

  const { data, isLoading } = useDeals({
    status: status || undefined,
    type: type || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    limit: LIMIT,
    offset,
  });

  const openPayment = (dealId: string, clientName: string | null | undefined) => {
    setPaymentDealId(dealId);
    setPaymentClientName(clientName ?? null);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold">Сделки</h1>
        <Link href="/deals/new">
          <Button size="sm">
            <Plus size={16} /> Новая сделка
          </Button>
        </Link>
      </div>

      <div className="bg-white rounded-xl border p-4 flex gap-3 flex-wrap">
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
          className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        >
          <option value="">Все статусы</option>
          {Object.entries(DEAL_STATUS_LABELS).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
        <select
          value={type}
          onChange={(e) => {
            setType(e.target.value);
            setOffset(0);
          }}
          className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        >
          <option value="">Все типы</option>
          {Object.entries(DEAL_TYPE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <span className="whitespace-nowrap">С</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setOffset(0);
            }}
            className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          />
        </label>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <span className="whitespace-nowrap">По</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setOffset(0);
            }}
            className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          />
        </label>
        {(dateFrom || dateTo) && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setDateFrom("");
              setDateTo("");
              setOffset(0);
            }}
          >
            Сбросить период
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : (
        <>
          <div className="md:hidden space-y-2">
            {data?.items.map((deal) => (
              <div
                key={deal.id}
                className="bg-white rounded-xl border p-4 space-y-2"
              >
                <Link href={`/deals/${deal.id}`} className="block hover:opacity-90">
                  <p className="font-semibold text-[#1a3a5c]">{deal.client_name ?? "—"}</p>
                  <div className="flex items-center gap-2 flex-wrap mt-1">
                    <span className="text-sm">{DEAL_TYPE_LABELS[deal.type]}</span>
                    <Badge className={DEAL_STATUS_COLORS[deal.status]}>
                      {DEAL_STATUS_LABELS[deal.status]}
                    </Badge>
                  </div>
                  <p className="text-lg font-bold text-[#1a3a5c] mt-0.5">
                    {formatCurrency(deal.total)}
                  </p>
                  <p className="text-xs text-gray-500">
                    {deal.duration_months} мес.
                    {deal.start_date && ` · с ${formatDate(deal.start_date)}`}
                  </p>
                </Link>
                <div className="flex gap-2">
                  {PAYABLE_STATUSES.has(deal.status) && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => openPayment(deal.id, deal.client_name)}
                    >
                      <CreditCard size={14} /> Платёж
                    </Button>
                  )}
                  <Link href={`/deals/${deal.id}`} className="flex-1">
                    <Button size="sm" variant="ghost" className="w-full">
                      Открыть
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
            {!data?.items.length && (
              <p className="text-center text-gray-500 py-8">Сделок нет</p>
            )}
          </div>

          <div className="hidden md:block bg-white rounded-xl border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Клиент</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Тип</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Статус</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Сумма</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Срок</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Дата</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-600">Действия</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data?.items.map((deal) => (
                    <tr key={deal.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-[#1a3a5c]">
                        {deal.client_name ?? "—"}
                      </td>
                      <td className="px-4 py-3">{DEAL_TYPE_LABELS[deal.type]}</td>
                      <td className="px-4 py-3">
                        <Badge className={DEAL_STATUS_COLORS[deal.status]}>
                          {DEAL_STATUS_LABELS[deal.status]}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">{formatCurrency(deal.total)}</td>
                      <td className="px-4 py-3">{deal.duration_months} мес.</td>
                      <td className="px-4 py-3 text-gray-500">
                        {deal.start_date ? formatDate(deal.start_date) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          {PAYABLE_STATUSES.has(deal.status) && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => openPayment(deal.id, deal.client_name)}
                            >
                              <CreditCard size={14} /> Платёж
                            </Button>
                          )}
                          <Link
                            href={`/deals/${deal.id}`}
                            className="text-[#1a3a5c] hover:underline text-xs font-medium"
                          >
                            Открыть →
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!data?.items.length && (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-gray-500">
                        Сделок нет
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {data && data.total > LIMIT && (
              <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
                <p className="text-sm text-gray-500">{data.total} сделок</p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                    disabled={offset === 0}
                  >
                    Назад
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setOffset(offset + LIMIT)}
                    disabled={offset + LIMIT >= data.total}
                  >
                    Далее
                  </Button>
                </div>
              </div>
            )}
          </div>

          {data && data.total > LIMIT && (
            <div className="md:hidden flex items-center justify-between pt-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setOffset(Math.max(0, offset - LIMIT))}
                disabled={offset === 0}
              >
                Назад
              </Button>
              <span className="text-sm text-gray-500">
                {Math.floor(offset / LIMIT) + 1} / {Math.ceil(data.total / LIMIT)}
              </span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setOffset(offset + LIMIT)}
                disabled={offset + LIMIT >= data.total}
              >
                Далее
              </Button>
            </div>
          )}
        </>
      )}

      <RecordPaymentDialog
        dealId={paymentDealId}
        clientName={paymentClientName}
        onClose={() => {
          setPaymentDealId(null);
          setPaymentClientName(null);
        }}
        onRecorded={() => qc.invalidateQueries({ queryKey: ["deals"] })}
      />
    </div>
  );
}
