"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  useOverdueCase,
  useSbCaseContext,
  useContactLogs,
  useAddContactLog,
  usePaymentPromises,
  useAddPromise,
  useUpdateCaseStatus,
  useUpdateCaseNotes,
} from "@/hooks/useSb";
import { DocumentsSection } from "@/components/features/shared/DocumentsSection";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  formatDate,
  formatDateTime,
  formatCurrency,
  formatPhone,
  OVERDUE_STATUS_LABELS,
  CONTACT_TYPE_LABELS,
  DEAL_TYPE_LABELS,
  DEAL_STATUS_LABELS,
  PAYMENT_METHOD_LABELS,
} from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { ArrowLeft, CreditCard, Phone, Calendar, MessageSquare, Send } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";
import { SMS_TEMPLATES } from "@/lib/notificationTemplates";

const STATUS_COLORS: Record<string, string> = {
  new: "bg-red-100 text-red-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  agreed: "bg-blue-100 text-blue-800",
  closed: "bg-green-100 text-green-800",
};

const TABS = ["Контакты", "Обещания", "Платежи", "Документы", "Реструктуризация"] as const;
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
  const [internalNotes, setInternalNotes] = useState("");

  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [paidAt, setPaidAt] = useState(new Date().toISOString().slice(0, 10));

  const { data: overdueCase, isLoading } = useOverdueCase(id);
  const { data: caseContext } = useSbCaseContext(id);
  const updateNotes = useUpdateCaseNotes(id);
  const { data: contactLogs } = useContactLogs(id);
  const { data: promises } = usePaymentPromises(id);
  const addContact = useAddContactLog(id);
  const addPromise = useAddPromise(id);
  const updateStatus = useUpdateCaseStatus();
  const qc = useQueryClient();

  const sendQuickSms = useMutation({
    mutationFn: () =>
      api.post("/api/notifications/send", {
        client_id: caseContext?.client_id,
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
    queryKey: ["restructurings-for-case", overdueCase?.deal_id],
    queryFn: async () => {
      const { data } = await api.get(`/api/deals/${overdueCase!.deal_id}/restructurings`);
      return data as { id: string; deal_id: string; status: string; reason: string; created_at: string; decision_comment: string | null }[];
    },
    enabled: !!overdueCase?.deal_id,
  });

  const { data: dealPayments } = useQuery({
    queryKey: ["deal-payments", overdueCase?.deal_id],
    queryFn: async () => {
      const { data } = await api.get(`/api/payments/deal/${overdueCase!.deal_id}`, { params: { limit: 20 } });
      return data as { items: { id: string; amount: string; paid_at: string; method: string; created_at: string }[] };
    },
    enabled: !!overdueCase?.deal_id,
  });

  const recordPayment = useMutation({
    mutationFn: () =>
      api.post("/api/payments/allocate", {
        deal_id: overdueCase!.deal_id,
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
      qc.invalidateQueries({ queryKey: ["deal-payments", overdueCase?.deal_id] });
      qc.invalidateQueries({ queryKey: ["sb-case-context", id] });
      qc.invalidateQueries({ queryKey: ["sb-cases", id] });
      qc.invalidateQueries({ queryKey: ["sb-cases"] });
      qc.invalidateQueries({ queryKey: ["sb-dashboard"] });
      qc.invalidateQueries({ queryKey: ["sb-stats"] });
    },
    onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  const pendingSchedules = caseContext?.pending_schedules ?? [];
  const totalScheduleRemaining = pendingSchedules.reduce(
    (sum, s) => sum + Math.max(0, parseFloat(s.amount) - parseFloat(s.paid_amount)),
    0
  );

  useEffect(() => {
    if (overdueCase?.internal_notes != null) {
      setInternalNotes(overdueCase.internal_notes ?? "");
    }
  }, [overdueCase?.internal_notes]);

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
        <div className="flex gap-2 flex-wrap">
          {caseContext?.client_id && (
            <Button size="sm" variant="outline" onClick={() => setShowQuickSms(!showQuickSms)}>
              <Send size={16} /> SMS клиенту
            </Button>
          )}
          {pendingSchedules.length > 0 && overdueCase.status !== "closed" && (
            <Button size="sm" variant="outline" onClick={() => setActiveTab("Платежи")}>
              <CreditCard size={16} /> Платёж
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

      {caseContext && (
        <div className="bg-white rounded-xl border p-4 grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500 text-xs mb-1">Клиент</p>
            <Link href={`/sb/clients/${caseContext.client_id}`} className="font-semibold text-[#1a3a5c] hover:underline">
              {caseContext.client_name}
            </Link>
            {caseContext.client_phone && (
              <p className="text-gray-600 mt-0.5">{formatPhone(caseContext.client_phone)}</p>
            )}
          </div>
          <div>
            <p className="text-gray-500 text-xs mb-1">Что купил</p>
            <p className="font-semibold">{caseContext.purchase_summary}</p>
            <p className="text-gray-600 mt-0.5">
              {DEAL_TYPE_LABELS[caseContext.deal_type]} · {formatCurrency(caseContext.deal_total)} ·{" "}
              {DEAL_STATUS_LABELS[caseContext.deal_status]}
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-xs mb-1">Менеджер (оформил)</p>
            <p className="font-semibold">{caseContext.manager_name}</p>
            {caseContext.next_schedule_due_date && (
              <p className="text-xs text-gray-500 mt-1">
                След. платёж: {formatDate(caseContext.next_schedule_due_date)} —{" "}
                {formatCurrency(caseContext.next_schedule_amount ?? 0)}
              </p>
            )}
          </div>
          <div className="sm:col-span-2">
            <p className="text-gray-500 text-xs mb-1">Просроченный долг</p>
            <p className="font-bold text-red-600">
              {formatCurrency(overdueCase.total_debt)} · {overdueCase.days_overdue} дн.
            </p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border p-4 space-y-2">
        <label className="text-sm font-medium">Внутренние заметки (только СБ)</label>
        <textarea
          value={internalNotes}
          onChange={(e) => setInternalNotes(e.target.value)}
          rows={3}
          className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        />
        <Button
          size="sm"
          variant="outline"
          loading={updateNotes.isPending}
          onClick={() =>
            updateNotes.mutate(internalNotes.trim() || null, {
              onSuccess: () => toast({ title: "Заметки сохранены" }),
            })
          }
        >
          Сохранить заметки
        </Button>
      </div>

      {/* Quick SMS */}
      {showQuickSms && (
        <div className="bg-white rounded-xl border p-4 space-y-3">
          <label className="text-sm font-medium">Быстрый SMS клиенту</label>
          <div className="flex flex-wrap gap-2">
            {SMS_TEMPLATES.map((t) => (
              <button
                key={t.id}
                type="button"
                className="text-xs px-2 py-1 border rounded-lg hover:bg-gray-50"
                onClick={() => setQuickSmsText(t.text)}
              >
                {t.label}
              </button>
            ))}
          </div>
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
          <p className="text-xs text-gray-500 mb-1">Просроченный долг</p>
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

      {/* Payments */}
      {activeTab === "Платежи" && (
        <div className="space-y-4">
          {pendingSchedules.length > 0 && overdueCase.status !== "closed" ? (
            <div className="bg-white rounded-xl border p-5 space-y-4">
              <div>
                <h3 className="font-semibold">Зафиксировать платёж</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Сумма автоматически спишется с ближайших неоплаченных строк графика.
                  Остаток по графику: {formatCurrency(totalScheduleRemaining)}
                </p>
              </div>
              {pendingSchedules.length > 0 && (
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
              )}
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
                      <option key={v} value={v}>{l}</option>
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
          ) : (
            <p className="text-sm text-gray-500 bg-white rounded-xl border p-4">
              Нет неоплаченных строк графика или дело закрыто.
            </p>
          )}

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
