"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  useOverdueCase,
  useContactLogs,
  useAddContactLog,
  usePaymentPromises,
  useAddPromise,
  useUpdateCaseStatus,
} from "@/hooks/useSb";
import { DocumentsSection } from "@/components/features/shared/DocumentsSection";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  formatDate,
  formatDateTime,
  formatCurrency,
  OVERDUE_STATUS_LABELS,
  CONTACT_TYPE_LABELS,
} from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { ArrowLeft, Phone, Calendar, MessageSquare, Send } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";

const STATUS_COLORS: Record<string, string> = {
  new: "bg-red-100 text-red-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  agreed: "bg-blue-100 text-blue-800",
  closed: "bg-green-100 text-green-800",
};

const TABS = ["Контакты", "Обещания", "Документы", "Реструктуризация"] as const;
type Tab = (typeof TABS)[number];

export default function SbCaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("Контакты");

  // Contact log form state
  const [contactType, setContactType] = useState("call");
  const [contactResult, setContactResult] = useState("");
  const [nextAction, setNextAction] = useState("");

  // Promise form state
  const [promiseDate, setPromiseDate] = useState(new Date().toISOString().slice(0, 10));
  const [promiseAmount, setPromiseAmount] = useState("");

  // Restructure form state
  const [restructureReason, setRestructureReason] = useState("");

  const [quickSmsText, setQuickSmsText] = useState("");
  const [showQuickSms, setShowQuickSms] = useState(false);

  const { data: overdueCase, isLoading } = useOverdueCase(id);
  const { data: contactLogs } = useContactLogs(id);
  const { data: promises } = usePaymentPromises(id);
  const addContact = useAddContactLog(id);
  const addPromise = useAddPromise(id);
  const updateStatus = useUpdateCaseStatus();
  const qc = useQueryClient();

  // Load deal + client info for SMS
  const { data: dealInfo } = useQuery({
    queryKey: ["deal-for-case", overdueCase?.deal_id],
    queryFn: async () => {
      if (!overdueCase?.deal_id) return null;
      const { data } = await api.get(`/api/deals/${overdueCase.deal_id}`);
      return data;
    },
    enabled: !!overdueCase?.deal_id,
  });

  const sendQuickSms = useMutation({
    mutationFn: () =>
      api.post("/api/notifications/send", {
        client_id: dealInfo?.client_id,
        channel: "sms",
        message: quickSmsText,
      }),
    onSuccess: () => {
      toast({ title: "SMS отправлен клиенту" });
      setQuickSmsText("");
      setShowQuickSms(false);
    },
    onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  const requestRestructure = useMutation({
    mutationFn: () =>
      api.post(`/api/sb/cases/${id}/restructure`, { reason: restructureReason }),
    onSuccess: () => {
      toast({ title: "Запрос на реструктуризацию отправлен" });
      setRestructureReason("");
      qc.invalidateQueries({ queryKey: ["restructurings-for-case", id] });
    },
    onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  const { data: caseRestructurings } = useQuery({
    queryKey: ["restructurings-for-case", id],
    queryFn: async () => {
      const { data } = await api.get("/api/director/approval/restructurings");
      return (data as { id: string; deal_id: string; status: string; reason: string; created_at: string; decision_comment: string | null }[])
        .filter((r) => r.deal_id === overdueCase?.deal_id);
    },
    enabled: !!overdueCase?.deal_id,
  });

  if (isLoading) {
    return <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" /></div>;
  }
  if (!overdueCase) return <p className="text-center py-8">Дело не найдено</p>;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link href="/sb/cases">
          <Button variant="ghost" size="icon"><ArrowLeft size={20} /></Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold">Дело #{id.slice(0, 8)}</h1>
          <Badge className={STATUS_COLORS[overdueCase.status]}>
            {OVERDUE_STATUS_LABELS[overdueCase.status]}
          </Badge>
        </div>
        <div className="flex gap-2">
          {dealInfo?.client_id && (
            <Button size="sm" variant="outline" onClick={() => setShowQuickSms(!showQuickSms)}>
              <Send size={16} /> SMS клиенту
            </Button>
          )}
          {overdueCase.status !== "closed" && (
            <Button
              size="sm"
              variant="destructive"
              onClick={() =>
                updateStatus.mutate(
                  { caseId: id, status: "closed" },
                  {
                    onSuccess: () => {
                      toast({ title: "Дело закрыто" });
                      qc.invalidateQueries({ queryKey: ["sb-cases", id] });
                    },
                  }
                )
              }
            >
              Закрыть дело
            </Button>
          )}
          {overdueCase.status === "new" && (
            <Button
              size="sm"
              onClick={() =>
                updateStatus.mutate(
                  { caseId: id, status: "in_progress" },
                  {
                    onSuccess: () => qc.invalidateQueries({ queryKey: ["sb-cases", id] }),
                  }
                )
              }
            >
              Взять в работу
            </Button>
          )}
        </div>
      </div>

      {/* Quick SMS */}
      {showQuickSms && (
        <div className="bg-white rounded-xl border p-4 space-y-3">
          <label className="text-sm font-medium">Быстрый SMS клиенту</label>
          <textarea
            value={quickSmsText}
            onChange={(e) => setQuickSmsText(e.target.value)}
            rows={3}
            className="w-full text-sm border rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-[#1a3a5c] resize-none"
            placeholder="Текст SMS..."
          />
          <div className="flex gap-2">
            <Button size="sm" loading={sendQuickSms.isPending} disabled={!quickSmsText.trim()} onClick={() => sendQuickSms.mutate()}>
              Отправить
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowQuickSms(false)}>Отмена</Button>
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="bg-white rounded-xl border p-5 grid grid-cols-2 sm:grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">Общий долг</p>
          <p className="text-2xl font-bold text-red-600">{formatCurrency(overdueCase.total_debt)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Дней просрочки</p>
          <p className="text-2xl font-bold">{overdueCase.days_overdue}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Создано</p>
          <p className="font-medium">{formatDate(overdueCase.created_at)}</p>
        </div>
        <div>
          <Link href={`/deals/${overdueCase.deal_id}`} className="text-[#1a3a5c] hover:underline text-sm font-medium">
            Открыть сделку →
          </Link>
        </div>
      </div>

      {/* Tabs */}
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
          </button>
        ))}
      </div>

      {/* Contact logs */}
      {activeTab === "Контакты" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border p-5 space-y-4">
            <h3 className="font-semibold">Новый контакт</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1">Тип</label>
                <select
                  value={contactType}
                  onChange={(e) => setContactType(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                >
                  {Object.entries(CONTACT_TYPE_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Следующий шаг</label>
                <input
                  type="text"
                  value={nextAction}
                  onChange={(e) => setNextAction(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                  placeholder="Позвонить завтра..."
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Результат *</label>
              <textarea
                value={contactResult}
                onChange={(e) => setContactResult(e.target.value)}
                rows={3}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c] resize-none"
                placeholder="Описание результата контакта..."
              />
            </div>
            <Button
              size="sm"
              loading={addContact.isPending}
              onClick={() => {
                if (!contactResult.trim()) return;
                addContact.mutate(
                  {
                    type: contactType as "call",
                    result: contactResult,
                    next_action: nextAction || null,
                    next_action_date: null,
                  },
                  {
                    onSuccess: () => {
                      toast({ title: "Контакт записан" });
                      setContactResult("");
                      setNextAction("");
                    },
                    onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
                  }
                );
              }}
            >
              Записать контакт
            </Button>
          </div>

          <div className="space-y-3">
            {contactLogs?.map((log) => (
              <div key={log.id} className="bg-white rounded-xl border p-4">
                <div className="flex items-center justify-between mb-2">
                  <Badge className="bg-gray-100 text-gray-700">
                    {CONTACT_TYPE_LABELS[log.type]}
                  </Badge>
                  <span className="text-xs text-gray-500">{formatDateTime(log.created_at)}</span>
                </div>
                <p className="text-sm">{log.result}</p>
                {log.next_action && (
                  <p className="text-xs text-[#1a3a5c] mt-1">→ {log.next_action}</p>
                )}
              </div>
            ))}
            {!contactLogs?.length && (
              <p className="text-center text-gray-500 py-4">Контактов пока нет</p>
            )}
          </div>
        </div>
      )}

      {/* Promises */}
      {activeTab === "Обещания" && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border p-5 space-y-3">
            <h3 className="font-semibold">Новое обещание</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1">Дата обещания</label>
                <input
                  type="date"
                  value={promiseDate}
                  onChange={(e) => setPromiseDate(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Сумма (₽)</label>
                <input
                  type="number"
                  value={promiseAmount}
                  onChange={(e) => setPromiseAmount(e.target.value)}
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                  placeholder="50000"
                />
              </div>
            </div>
            <Button
              size="sm"
              loading={addPromise.isPending}
              onClick={() => {
                addPromise.mutate(
                  { promised_date: promiseDate, promised_amount: promiseAmount },
                  {
                    onSuccess: () => {
                      toast({ title: "Обещание зафиксировано" });
                      setPromiseAmount("");
                    },
                    onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
                  }
                );
              }}
            >
              Зафиксировать
            </Button>
          </div>

          <div className="space-y-2">
            {promises?.map((p) => (
              <div key={p.id} className="bg-white rounded-xl border p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{formatCurrency(p.promised_amount)}</p>
                  <p className="text-sm text-gray-500">к {formatDate(p.promised_date)}</p>
                </div>
                <Badge className={p.is_fulfilled ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-700"}>
                  {p.is_fulfilled ? "Выполнено" : "Ожидается"}
                </Badge>
              </div>
            ))}
            {!promises?.length && (
              <p className="text-center text-gray-500 py-4">Обещаний нет</p>
            )}
          </div>
        </div>
      )}

      {/* Documents */}
      {activeTab === "Документы" && (
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold mb-4">Документы по делу</h3>
          <DocumentsSection
            entityType="overdue_case"
            entityId={id}
            availableDocTypes={["act", "notification", "photo", "other"]}
          />
        </div>
      )}

      {/* Restructuring */}
      {activeTab === "Реструктуризация" && (
        <div className="space-y-4">
          {/* Existing restructuring requests */}
          {caseRestructurings && caseRestructurings.length > 0 && (
            <div className="bg-white rounded-xl border p-5 space-y-3">
              <h3 className="font-semibold">История запросов</h3>
              {caseRestructurings.map((r) => {
                const statusConfig: Record<string, { label: string; className: string }> = {
                  pending: { label: "Ожидает решения", className: "bg-yellow-100 text-yellow-800" },
                  approved: { label: "Одобрена", className: "bg-green-100 text-green-800" },
                  rejected: { label: "Отклонена", className: "bg-red-100 text-red-800" },
                };
                const cfg = statusConfig[r.status] ?? { label: r.status, className: "bg-gray-100 text-gray-700" };
                return (
                  <div key={r.id} className="border rounded-lg p-3 space-y-1">
                    <div className="flex items-center justify-between">
                      <Badge className={cfg.className}>{cfg.label}</Badge>
                      <span className="text-xs text-gray-500">{formatDate(r.created_at)}</span>
                    </div>
                    <p className="text-sm">{r.reason}</p>
                    {r.decision_comment && (
                      <p className="text-xs text-gray-500 italic">Комментарий: {r.decision_comment}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* New request form */}
          <div className="bg-white rounded-xl border p-5 space-y-4">
            <h3 className="font-semibold">Новый запрос на реструктуризацию</h3>
            <p className="text-sm text-gray-500">
              Запрос будет отправлен руководителю на согласование.
            </p>
            <div>
              <label className="block text-sm font-medium mb-1">Обоснование *</label>
              <textarea
                value={restructureReason}
                onChange={(e) => setRestructureReason(e.target.value)}
                rows={4}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c] resize-none"
                placeholder="Клиент временно испытывает финансовые трудности, предлагает..."
              />
            </div>
            <Button
              size="sm"
              loading={requestRestructure.isPending}
              disabled={restructureReason.length < 10}
              onClick={() => requestRestructure.mutate()}
            >
              Отправить запрос
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
