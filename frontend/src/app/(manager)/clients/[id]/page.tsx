"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useClient, useArchiveClient, useUpdateClient } from "@/hooks/useClients";
import { useDeals } from "@/hooks/useDeals";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  formatDate,
  formatPhone,
  formatCurrency,
  DEAL_STATUS_LABELS,
  DEAL_STATUS_COLORS,
  DEAL_TYPE_LABELS,
} from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage, isForbidden } from "@/lib/axios";
import { ArrowLeft, Archive, Phone, FileText, Plus, X, Tag } from "lucide-react";
import { DocumentsSection } from "@/components/features/shared/DocumentsSection";
import api from "@/lib/axios";
import { SMS_TEMPLATES } from "@/lib/notificationTemplates";
import { useMutation } from "@tanstack/react-query";

const TABS = ["Сделки", "Уведомления", "Документы"] as const;
type Tab = (typeof TABS)[number];

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("Сделки");
  const [smsMessage, setSmsMessage] = useState("");
  const [showSmsForm, setShowSmsForm] = useState(false);

  const [newTag, setNewTag] = useState("");

  const { data: client, isLoading, isError, error, refetch } = useClient(id);
  const { data: dealsData } = useDeals({ client_id: id, limit: 100 });
  const archiveClient = useArchiveClient();
  const updateClient = useUpdateClient(id);

  const sendSms = useMutation({
    mutationFn: () =>
      api.post("/api/notifications/send", {
        client_id: id,
        channel: "sms",
        message: smsMessage,
      }),
    onSuccess: () => {
      toast({ title: "SMS отправлен" });
      setSmsMessage("");
      setShowSmsForm(false);
    },
    onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  if (isLoading) {
    return <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" /></div>;
  }
  if (isError && isForbidden(error)) {
    return <p className="text-center py-8 text-gray-600">Нет доступа к этому клиенту</p>;
  }
  if (!client) return <p className="text-center py-8 text-gray-500">Клиент не найден</p>;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/clients">
          <Button variant="ghost" size="icon"><ArrowLeft size={20} /></Button>
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold truncate">{client.full_name}</h1>
          <p className="text-sm text-gray-500">{formatPhone(client.phone)}</p>
        </div>
        <div className="flex items-center gap-2">
          {!client.is_archived && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSmsForm(!showSmsForm)}
            >
              <Phone size={16} /> SMS
            </Button>
          )}
        </div>
      </div>

      {showSmsForm && (
        <div className="bg-white rounded-xl border p-4 space-y-3">
          <label className="text-sm font-medium">Текст SMS клиенту</label>
          <div className="flex flex-wrap gap-2">
            {SMS_TEMPLATES.map((t) => (
              <button
                key={t.id}
                type="button"
                className="text-xs px-2 py-1 border rounded-lg hover:bg-gray-50"
                onClick={() => setSmsMessage(t.text)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <textarea
            value={smsMessage}
            onChange={(e) => setSmsMessage(e.target.value)}
            rows={3}
            className="w-full text-sm border rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            placeholder="Текст сообщения..."
          />
          <div className="flex gap-2">
            <Button size="sm" loading={sendSms.isPending} onClick={() => sendSms.mutate()}>
              Отправить
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowSmsForm(false)}>
              Отмена
            </Button>
          </div>
        </div>
      )}

      {/* Profile card */}
      <div className="bg-white rounded-xl border p-5 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <InfoItem label="Паспорт">{client.passport || "—"}</InfoItem>
        <InfoItem label="Адрес">{client.address || "—"}</InfoItem>
        <InfoItem label="Менеджер">
          {client.manager_name ?? "—"}
        </InfoItem>
        <InfoItem label="Добавлен">{formatDate(client.created_at)}</InfoItem>
        <InfoItem label="Статус">
          {client.is_archived ? (
            <Badge className="bg-gray-100 text-gray-600">Архив</Badge>
          ) : (
            <Badge className="bg-green-100 text-green-800">Активный</Badge>
          )}
        </InfoItem>
        {client.notes && (
          <InfoItem label="Заметки" className="col-span-full">
            <p className="whitespace-pre-line text-sm">{client.notes}</p>
          </InfoItem>
        )}
        <InfoItem label="Теги" className="col-span-full">
          <div className="flex flex-wrap gap-2 items-center">
            {(client.tags as string[] ?? []).map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 bg-[#1a3a5c]/10 text-[#1a3a5c] text-xs font-medium px-2.5 py-1 rounded-full"
              >
                {tag}
                <button
                  onClick={() => {
                    const newTags = (client.tags as string[]).filter((t) => t !== tag);
                    updateClient.mutate({ tags: newTags }, { onSuccess: () => refetch() });
                  }}
                  className="hover:text-red-600 transition-colors"
                >
                  <X size={12} />
                </button>
              </span>
            ))}
            <form
              className="flex items-center gap-1"
              onSubmit={(e) => {
                e.preventDefault();
                const trimmed = newTag.trim();
                if (!trimmed) return;
                const existing = (client.tags as string[]) ?? [];
                if (existing.includes(trimmed)) return;
                updateClient.mutate(
                  { tags: [...existing, trimmed] },
                  { onSuccess: () => { refetch(); setNewTag(""); } }
                );
              }}
            >
              <input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                placeholder="+ добавить тег"
                className="text-xs border rounded-full px-2.5 py-1 focus:outline-none focus:ring-1 focus:ring-[#1a3a5c] w-28"
              />
            </form>
          </div>
        </InfoItem>
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

      {/* Tab content */}
      {activeTab === "Сделки" && (
        <div className="space-y-3">
          <div className="flex justify-end">
            <Link href={`/deals/new?client_id=${id}`}>
              <Button size="sm"><Plus size={16} /> Новая сделка</Button>
            </Link>
          </div>
          {dealsData?.items.map((deal) => (
            <Link
              key={deal.id}
              href={`/deals/${deal.id}`}
              className="block bg-white rounded-xl border p-4 hover:shadow-sm transition-shadow"
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium block">
                    {deal.purchase_summary ?? DEAL_TYPE_LABELS[deal.type]}
                  </span>
                  <span className="text-gray-500 text-sm">
                    {DEAL_TYPE_LABELS[deal.type]} · {formatCurrency(deal.total)}
                    {deal.manager_name && ` · ${deal.manager_name}`}
                  </span>
                </div>
                <Badge className={DEAL_STATUS_COLORS[deal.status]}>
                  {DEAL_STATUS_LABELS[deal.status]}
                </Badge>
              </div>
              <p className="text-sm text-gray-500 mt-1">
                {deal.duration_months} мес.{" "}
                {deal.start_date && `• с ${formatDate(deal.start_date)}`}
              </p>
            </Link>
          ))}
          {!dealsData?.items.length && (
            <p className="text-center text-gray-500 py-8">Сделок нет</p>
          )}
        </div>
      )}

      {activeTab === "Уведомления" && (
        <p className="text-gray-500 text-center py-8">История уведомлений</p>
      )}
      {activeTab === "Документы" && (
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold mb-4">Документы клиента</h3>
          <DocumentsSection
            entityType="client"
            entityId={id}
            availableDocTypes={["contract", "collateral", "photo", "other"]}
          />
        </div>
      )}
    </div>
  );
}

function InfoItem({
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
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <div className="font-medium">{children}</div>
    </div>
  );
}
