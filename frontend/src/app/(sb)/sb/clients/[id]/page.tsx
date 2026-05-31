"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  formatCurrency,
  formatDate,
  formatPhone,
  DEAL_TYPE_LABELS,
  DEAL_STATUS_LABELS,
  OVERDUE_STATUS_LABELS,
} from "@/lib/utils";
import { ArrowLeft } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  new: "bg-red-100 text-red-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  agreed: "bg-blue-100 text-blue-800",
  closed: "bg-green-100 text-green-800",
};

interface ClientSearchProfile {
  id: string;
  full_name: string;
  phone: string | null;
  manager_id: string;
  manager_name: string;
  overdue_cases: {
    case_id: string;
    deal_id: string;
    status: string;
    total_debt: string;
    days_overdue: number;
    sb_user_id: string | null;
  }[];
  deals: {
    deal_id: string;
    deal_type: string;
    deal_status: string;
    deal_total: string;
    duration_months: number;
    start_date: string | null;
    product_description: string | null;
    purchase_summary: string;
    manager_id: string;
    manager_name: string;
    case_id: string | null;
    case_status: string | null;
    schedules: {
      id: string;
      installment_number: number;
      due_date: string;
      amount: string;
      paid_amount: string;
      status: string;
    }[];
  }[];
}

export default function SbClientPage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["search-client-profile", id],
    queryFn: async () => {
      const { data: res } = await api.get(`/api/search/client/${id}`);
      return res as ClientSearchProfile;
    },
  });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
      </div>
    );
  }
  if (isError || !data) {
    return <p className="text-center py-8 text-gray-600">Клиент не найден или нет доступа</p>;
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link href="/sb/cases">
          <Button variant="ghost" size="icon">
            <ArrowLeft size={20} />
          </Button>
        </Link>
        <div>
          <h1 className="text-xl font-bold">{data.full_name}</h1>
          {data.phone && <p className="text-sm text-gray-500">{formatPhone(data.phone)}</p>}
          <p className="text-sm text-gray-600 mt-1">
            Менеджер клиента: <span className="font-medium">{data.manager_name}</span>
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <h2 className="font-semibold">Дела в СБ</h2>
        {data.overdue_cases.length === 0 ? (
          <p className="text-sm text-gray-500">Открытых дел нет</p>
        ) : (
          data.overdue_cases.map((c) => {
            const dealInfo = data.deals.find((d) => d.case_id === c.case_id);
            return (
            <Link
              key={c.case_id}
              href={`/sb/cases/${c.case_id}`}
              className="block bg-white rounded-xl border p-4 hover:shadow-sm"
            >
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <Badge className={STATUS_COLORS[c.status] ?? "bg-gray-100"}>
                  {OVERDUE_STATUS_LABELS[c.status] ?? c.status}
                </Badge>
                {!c.sb_user_id && (
                  <span className="text-xs text-orange-600 font-medium">Не назначен</span>
                )}
              </div>
              <p className="text-lg font-bold text-red-600 mt-1">
                {formatCurrency(c.total_debt)} · {c.days_overdue} дн.
              </p>
              {dealInfo && (
                <p className="text-xs text-gray-500 mt-1">
                  {dealInfo.purchase_summary} · {dealInfo.manager_name}
                </p>
              )}
            </Link>
            );
          })
        )}
      </div>

      <div className="space-y-3">
        <h2 className="font-semibold">Рассрочки (сделки)</h2>
        {data.deals.map((deal) => (
          <div key={deal.deal_id} className="bg-white rounded-xl border p-4 space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <p className="font-medium">{deal.purchase_summary}</p>
                <p className="text-sm text-gray-500">
                  {DEAL_TYPE_LABELS[deal.deal_type]} · {formatCurrency(deal.deal_total)} ·{" "}
                  {deal.duration_months} мес.
                  {deal.start_date && ` · с ${formatDate(deal.start_date)}`}
                </p>
                <p className="text-sm text-gray-600 mt-0.5">
                  Оформил: <span className="font-medium">{deal.manager_name}</span>
                </p>
              </div>
              <Badge className="bg-gray-100 text-gray-700">
                {DEAL_STATUS_LABELS[deal.deal_status] ?? deal.deal_status}
              </Badge>
            </div>
            {deal.case_id && (
              <Link
                href={`/sb/cases/${deal.case_id}`}
                className="text-sm text-[#1a3a5c] font-medium hover:underline"
              >
                Открыть дело СБ →
              </Link>
            )}
            {deal.schedules.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-1 pr-2">№</th>
                      <th className="py-1 pr-2">Дата</th>
                      <th className="py-1 pr-2">Сумма</th>
                      <th className="py-1">Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deal.schedules.map((s) => (
                      <tr key={s.id} className="border-b last:border-0">
                        <td className="py-1.5 pr-2">{s.installment_number}</td>
                        <td className="py-1.5 pr-2">{formatDate(s.due_date)}</td>
                        <td className="py-1.5 pr-2">{formatCurrency(s.amount)}</td>
                        <td className="py-1.5">{s.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
        {data.deals.length === 0 && (
          <p className="text-sm text-gray-500">Сделок нет</p>
        )}
      </div>
    </div>
  );
}
