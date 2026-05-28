"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useClient, useUpdateKyc, useArchiveClient, useUpdateClient } from "@/hooks/useClients";
import { useDeals } from "@/hooks/useDeals";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  formatDate,
  formatPhone,
  formatCurrency,
  KYC_STATUS_LABELS,
  KYC_STATUS_COLORS,
  DEAL_STATUS_LABELS,
  DEAL_STATUS_COLORS,
  DEAL_TYPE_LABELS,
} from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { ArrowLeft, Archive, Phone, FileText, Plus, X, Tag } from "lucide-react";
import { DocumentsSection } from "@/components/features/shared/DocumentsSection";
import api from "@/lib/axios";
import { useMutation, useQuery } from "@tanstack/react-query";

const TABS = ["Сделки", "Реструктуризации", "Уведомления", "Документы"] as const;
type Tab = (typeof TABS)[number];

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<Tab>("Сделки");
  const [smsMessage, setSmsMessage] = useState("");
  const [showSmsForm, setShowSmsForm] = useState(false);

  const [newTag, setNewTag] = useState("");

  const { data: client, isLoading, refetch } = useClient(id);
  const { data: dealsData } = useDeals({ client_id: id, limit: 100 });
  const updateKyc = useUpdateKyc(id);
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
        <InfoItem label="KYC статус">
          <div className="flex items-center gap-2">
            <Badge className={KYC_STATUS_COLORS[client.kyc_status]}>
              {KYC_STATUS_LABELS[client.kyc_status]}
            </Badge>
            {client.kyc_status !== "verified" && (
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  updateKyc.mutate("verified", {
                    onSuccess: () => refetch(),
                  })
                }
                className="text-xs h-7 px-2"
              >
                Подтвердить
              </Button>
            )}
          </div>
        </InfoItem>
        <InfoItem label="Паспорт">{client.passport || "—"}</InfoItem>
        <InfoItem label="Адрес">{client.address || "—"}</InfoItem>
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
                  <span className="font-medium">{DEAL_TYPE_LABELS[deal.type]}</span>
                  <span className="text-gray-500 text-sm ml-2">
                    {formatCurrency(deal.total)}
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

      {activeTab === "Реструктуризации" && (
        <RestructuringHistory clientId={id} dealsData={dealsData?.items ?? []} />
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

const R_STATUS_LABELS: Record<string, string> = {
  pending: "Ожидает",
  approved: "Одобрена",
  rejected: "Отклонена",
};
const R_STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
};

function RestructuringHistory({ clientId, dealsData }: { clientId: string; dealsData: { id: string }[] }) {
  const dealIds = dealsData.map((d) => d.id);
  const { data, isLoading } = useQuery({
    queryKey: ["restructurings", clientId],
    queryFn: async () => {
      // Fetch restructurings for each deal in parallel
      const results = await Promise.all(
        dealIds.map((dealId) =>
          api.get(`/api/deals/${dealId}`).then((r) => r.data)
        )
      );
      // Extract restructurings from deals
      const all: { deal_id: string; id: string; status: string; reason: string; created_at: string; decision_comment: string | null }[] = [];
      for (const deal of results) {
        if (deal.restructurings) {
          all.push(...deal.restructurings.map((r: typeof r & { deal_id: string }) => ({ ...r, deal_id: deal.id })));
        }
      }
      return all.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    },
    enabled: dealIds.length > 0,
  });

  // Use API endpoint directly
  const { data: restructurings, isLoading: loading } = useQuery({
    queryKey: ["client-restructurings", clientId],
    queryFn: async () => {
      const { data } = await api.get("/api/director/approval/restructurings");
      return data as { id: string; deal_id: string; status: string; reason: string; created_at: string; decision_comment: string | null }[];
    },
  });

  if (loading) return <div className="flex justify-center py-8"><div className="animate-spin h-6 w-6 border-2 border-[#1a3a5c] border-t-transparent rounded-full" /></div>;

  const filtered = (restructurings ?? []).filter((r) => dealIds.includes(r.deal_id));

  if (!filtered.length) return <p className="text-center text-gray-500 py-8">Реструктуризаций нет</p>;

  return (
    <div className="space-y-3">
      {filtered.map((r) => (
        <div key={r.id} className="bg-white rounded-xl border p-4">
          <div className="flex items-center justify-between mb-2">
            <Badge className={R_STATUS_COLORS[r.status]}>{R_STATUS_LABELS[r.status]}</Badge>
            <span className="text-xs text-gray-500">{formatDate(r.created_at)}</span>
          </div>
          <p className="text-sm">{r.reason}</p>
          {r.decision_comment && (
            <p className="text-xs text-gray-500 mt-1">Комментарий: {r.decision_comment}</p>
          )}
        </div>
      ))}
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
