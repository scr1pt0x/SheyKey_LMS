"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useDeal, useSubmitDeal, downloadMurabahaDocx } from "@/hooks/useDeals";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DocumentsSection } from "@/components/features/shared/DocumentsSection";
import { DealPaymentPanel } from "@/components/features/shared/DealPaymentPanel";
import {
  formatDate,
  formatCurrency,
  DEAL_TYPE_LABELS,
  DEAL_STATUS_LABELS,
  DEAL_STATUS_COLORS,
} from "@/lib/utils";
import {
  MURABAHA_CATEGORY_LABELS,
  MURABAHA_TARIFF_LABELS,
  type MurabahaCategory,
  type MurabahaTariffKey,
} from "@/lib/murabaha";
import { toast } from "@/hooks/useToast";
import { getErrorMessage, isForbidden } from "@/lib/axios";
import { ArrowLeft, Download } from "lucide-react";
import { useState } from "react";

const PAYABLE_STATUSES = new Set(["active", "overdue"]);

export default function DealDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: deal, isLoading, isError, error, refetch } = useDeal(id);
  const submitDeal = useSubmitDeal();
  const [docxLoading, setDocxLoading] = useState(false);

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
      </div>
    );
  }
  if (isError && isForbidden(error)) {
    return <p className="text-center py-8 text-gray-600">Нет доступа к этой сделке</p>;
  }
  if (!deal) return <p className="text-center py-8">Сделка не найдена</p>;

  const canRecordPayments = PAYABLE_STATUSES.has(deal.status);
  const murabahaParams = deal.params as Record<string, unknown> | null | undefined;

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <div className="flex items-start gap-3">
          <Link href="/deals" className="shrink-0">
            <Button variant="ghost" size="icon">
              <ArrowLeft size={20} />
            </Button>
          </Link>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl font-bold break-words">
              {deal.purchase_summary ?? DEAL_TYPE_LABELS[deal.type]}
            </h1>
            <p className="text-sm text-gray-500 mt-0.5 break-words">
              {DEAL_TYPE_LABELS[deal.type]} · {formatCurrency(deal.total)}
              {deal.manager_name && (
                <span className="hidden sm:inline">{` · оформил ${deal.manager_name}`}</span>
              )}
            </p>
            {deal.manager_name && (
              <p className="text-sm text-gray-500 mt-0.5 sm:hidden break-words">
                оформил {deal.manager_name}
              </p>
            )}
            <Badge className={`${DEAL_STATUS_COLORS[deal.status]} mt-1`}>
              {DEAL_STATUS_LABELS[deal.status]}
            </Badge>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 pl-[52px] sm:pl-0">
          {deal.status === "draft" && (
            <Button
              size="sm"
              className="w-full sm:w-auto"
              loading={submitDeal.isPending}
              onClick={() =>
                submitDeal.mutate(id, {
                  onSuccess: () => toast({ title: "Сделка оформлена" }),
                  onError: (err) =>
                    toast({
                      title: "Ошибка",
                      description: getErrorMessage(err),
                      variant: "destructive",
                    }),
                })
              }
            >
              Оформить сделку
            </Button>
          )}
          {deal.type === "murabaha" && (
            <Button
              size="sm"
              variant="outline"
              loading={docxLoading}
              onClick={async () => {
                setDocxLoading(true);
                try {
                  await downloadMurabahaDocx(id);
                  toast({ title: "Договор скачан" });
                } catch (err) {
                  toast({
                    title: "Ошибка",
                    description: getErrorMessage(err),
                    variant: "destructive",
                  });
                } finally {
                  setDocxLoading(false);
                }
              }}
            >
              <Download size={16} /> Скачать договор
            </Button>
          )}
        </div>
      </div>

      {deal.type === "murabaha" && murabahaParams?.product_category != null && (
        <div className="bg-white rounded-xl border p-5 grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
          {murabahaParams.contract_number != null && (
            <Info label="Номер договора">{String(murabahaParams.contract_number)}</Info>
          )}
          <Info label="Категория">
            {MURABAHA_CATEGORY_LABELS[murabahaParams.product_category as MurabahaCategory] ??
              String(murabahaParams.product_category)}
          </Info>
          {murabahaParams.tariff != null && (
            <Info label="Тариф">
              {MURABAHA_TARIFF_LABELS[murabahaParams.tariff as MurabahaTariffKey] ??
                String(murabahaParams.tariff)}
            </Info>
          )}
          {murabahaParams.down_payment_pct != null && (
            <Info label="Первоначальный взнос">
              {String(murabahaParams.down_payment_pct)}%
              {murabahaParams.down_payment_amount != null &&
                ` (${formatCurrency(String(murabahaParams.down_payment_amount))})`}
            </Info>
          )}
          {murabahaParams.monthly_payment != null && (
            <Info label="Ежемесячный платёж">
              {formatCurrency(String(murabahaParams.monthly_payment))}
            </Info>
          )}
        </div>
      )}

      <div className="bg-white rounded-xl border p-5 grid grid-cols-2 sm:grid-cols-3 gap-4">
        <Info label="Основная сумма">{formatCurrency(deal.principal)}</Info>
        <Info label="Наценка">{formatCurrency(deal.markup)}</Info>
        <Info label="Итого к выплате">
          <span className="text-lg font-bold">{formatCurrency(deal.total)}</span>
        </Info>
        <Info label="Срок">{deal.duration_months} мес.</Info>
        <Info label="Дата начала">{deal.start_date ? formatDate(deal.start_date) : "—"}</Info>
        <Info label="Дата окончания">{deal.end_date ? formatDate(deal.end_date) : "—"}</Info>
      </div>

      <DealPaymentPanel
        dealId={id}
        schedules={deal.payment_schedules}
        canRecord={canRecordPayments}
        onRecorded={() => refetch()}
      />

      <div className="bg-white rounded-xl border p-5">
        <h2 className="font-semibold mb-4">Документы</h2>
        <DocumentsSection
          entityType="deal"
          entityId={id}
          availableDocTypes={["contract", "collateral", "photo", "receipt", "other"]}
        />
      </div>

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
                <th className="text-left px-4 py-3 font-medium text-gray-600 hidden sm:table-cell">
                  Оплачено
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-600 hidden sm:table-cell">
                  Остаток
                </th>
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
                return (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">{s.installment_number}</td>
                    <td className="px-4 py-3">{formatDate(s.due_date)}</td>
                    <td className="px-4 py-3 font-medium">{formatCurrency(s.amount)}</td>
                    <td className="px-4 py-3 hidden sm:table-cell text-green-700">
                      {formatCurrency(s.paid_amount)}
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell text-gray-600">
                      {formatCurrency(remaining)}
                    </td>
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

function Info({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <div className="font-medium">{children}</div>
    </div>
  );
}
