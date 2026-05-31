"use client";

import { useState } from "react";
import Link from "next/link";
import {
  usePendingDeals,
  usePendingRestructurings,
  useApproveDeal,
  useRejectDeal,
  useApproveRestructuring,
  useRejectRestructuring,
  useStaffUsers,
} from "@/hooks/useDirector";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  formatDate,
  formatCurrency,
  DEAL_TYPE_LABELS,
} from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { CheckSquare } from "lucide-react";

const TABS = ["Сделки", "Реструктуризации"] as const;
type Tab = (typeof TABS)[number];

export default function ApprovalPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Сделки");
  const [rejectDealId, setRejectDealId] = useState<string | null>(null);
  const [rejectComment, setRejectComment] = useState("");
  const [rejectRId, setRejectRId] = useState<string | null>(null);
  const [approveManagers, setApproveManagers] = useState<Record<string, string>>({});

  const user = useAuthStore((s) => s.user);
  const { data: managers = [] } = useStaffUsers("manager");
  const { data: dealsData, isLoading: dealsLoading } = usePendingDeals();
  const { data: restructuringsData, isLoading: rLoading } = usePendingRestructurings();
  const approveDeal = useApproveDeal();
  const rejectDeal = useRejectDeal();
  const approveR = useApproveRestructuring();
  const rejectR = useRejectRestructuring();

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <CheckSquare size={22} className="text-[#1a3a5c]" />
        <h1 className="text-xl font-bold">Очередь согласования</h1>
      </div>

      <div className="border-b flex gap-6">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-[#1a3a5c] text-[#1a3a5c]"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab}
            {tab === "Сделки" && dealsData?.total > 0 && (
              <span className="ml-1.5 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
                {dealsData.total}
              </span>
            )}
          </button>
        ))}
      </div>

      {activeTab === "Сделки" && (
        <div className="space-y-3">
          {dealsLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
            </div>
          ) : dealsData?.items.length === 0 ? (
            <div className="bg-white rounded-xl border p-8 text-center text-gray-500">
              Нет сделок на согласовании
            </div>
          ) : (
            dealsData?.items.map((deal: {
              id: string;
              manager_id: string;
              type: string;
              total: string;
              duration_months: number;
              start_date: string | null;
              created_at: string;
            }) => (
              <div key={deal.id} className="bg-white rounded-xl border p-5">
                <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-lg">{formatCurrency(deal.total)}</p>
                      <Badge className="bg-yellow-100 text-yellow-800">
                        {DEAL_TYPE_LABELS[deal.type]}
                      </Badge>
                    </div>
                    <p className="text-sm text-gray-500">
                      {deal.duration_months} мес.{" "}
                      {deal.start_date && `• с ${formatDate(deal.start_date)}`}
                      {" • создана " + formatDate(deal.created_at)}
                    </p>
                  </div>
                  <Link
                    href={`/deals/${deal.id}`}
                    className="text-[#1a3a5c] hover:underline text-sm"
                    target="_blank"
                  >
                    Просмотреть сделку →
                  </Link>
                </div>

                {rejectDealId === deal.id ? (
                  <div className="space-y-2 mt-3 border-t pt-3">
                    <textarea
                      value={rejectComment}
                      onChange={(e) => setRejectComment(e.target.value)}
                      rows={2}
                      placeholder="Причина отклонения (обязательно)..."
                      className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-400"
                    />
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="destructive"
                        loading={rejectDeal.isPending}
                        disabled={rejectComment.length < 3}
                        onClick={() =>
                          rejectDeal.mutate(
                            { dealId: deal.id, comment: rejectComment },
                            {
                              onSuccess: () => {
                                toast({ title: "Сделка отклонена" });
                                setRejectDealId(null);
                                setRejectComment("");
                              },
                              onError: (err) =>
                                toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
                            }
                          )
                        }
                      >
                        Подтвердить отклонение
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setRejectDealId(null)}>
                        Отмена
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3 mt-3">
                    {user?.id === deal.manager_id && (
                      <div>
                        <label className="block text-xs font-medium text-gray-600 mb-1">
                          Ответственный менеджер (необязательно)
                        </label>
                        <select
                          value={approveManagers[deal.id] ?? ""}
                          onChange={(e) =>
                            setApproveManagers((prev) => ({
                              ...prev,
                              [deal.id]: e.target.value,
                            }))
                          }
                          className="w-full max-w-md px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                        >
                          <option value="">Оставить у руководителя</option>
                          {managers
                            .filter((m) => m.is_active)
                            .map((m) => (
                              <option key={m.id} value={m.id}>
                                {m.name}
                              </option>
                            ))}
                        </select>
                      </div>
                    )}
                    <div className="flex gap-2">
                    <Button
                      size="sm"
                      loading={approveDeal.isPending}
                      onClick={() =>
                        approveDeal.mutate(
                          {
                            dealId: deal.id,
                            responsible_manager_id:
                              approveManagers[deal.id] || undefined,
                          },
                          {
                            onSuccess: () => toast({ title: "Сделка одобрена" }),
                            onError: (err) =>
                              toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
                          }
                        )
                      }
                    >
                      Одобрить
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => setRejectDealId(deal.id)}
                    >
                      Отклонить
                    </Button>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "Реструктуризации" && (
        <div className="space-y-3">
          {rLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
            </div>
          ) : !restructuringsData?.length ? (
            <div className="bg-white rounded-xl border p-8 text-center text-gray-500">
              Нет запросов на реструктуризацию
            </div>
          ) : (
            (restructuringsData as { id: string; deal_id: string; reason: string; created_at: string }[]).map((r) => (
              <div key={r.id} className="bg-white rounded-xl border p-5">
                <p className="font-medium mb-1">Сделка #{r.deal_id.slice(0, 8)}</p>
                <p className="text-sm text-gray-600 mb-3">{r.reason}</p>
                <p className="text-xs text-gray-400 mb-3">{formatDate(r.created_at)}</p>
                {rejectRId === r.id ? (
                  <div className="space-y-2">
                    <textarea
                      value={rejectComment}
                      onChange={(e) => setRejectComment(e.target.value)}
                      rows={2}
                      placeholder="Причина отклонения..."
                      className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-red-400"
                    />
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="destructive"
                        loading={rejectR.isPending}
                        disabled={rejectComment.length < 3}
                        onClick={() =>
                          rejectR.mutate(
                            { rId: r.id, comment: rejectComment },
                            {
                              onSuccess: () => {
                                toast({ title: "Отклонено" });
                                setRejectRId(null);
                              },
                            }
                          )
                        }
                      >
                        Подтвердить
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setRejectRId(null)}>Отмена</Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      loading={approveR.isPending}
                      onClick={() =>
                        approveR.mutate(
                          { rId: r.id },
                          { onSuccess: () => toast({ title: "Реструктуризация одобрена" }) }
                        )
                      }
                    >
                      Одобрить
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => setRejectRId(r.id)}>
                      Отклонить
                    </Button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
