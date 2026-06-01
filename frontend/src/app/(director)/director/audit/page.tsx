"use client";

import { useState } from "react";
import { useAuditLog, useManagerControl } from "@/hooks/useDirector";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/utils";
import { Shield, Download } from "lucide-react";
import api from "@/lib/axios";

const LIMIT = 50;

const ACTION_LABELS: Record<string, string> = {
  CREATE: "Создание",
  UPDATE: "Изменение",
  DELETE: "Удаление",
  LOGIN: "Вход",
  LOGOUT: "Выход",
  DEAL_APPROVED: "Сделка одобрена",
  DEAL_REJECTED: "Сделка отклонена",
  PAYMENT_RECORDED: "Платёж зафиксирован",
  PAYMENT_CONFIRMED: "Платёж подтверждён",
  RECEIPT_ATTACHED: "Чек прикреплён",
  ARCHIVE: "Архивация",
  ADD_NOTE: "Заметка",
  STATUS_CHANGE: "Смена статуса",
  CASE_ASSIGNED: "Дело назначено",
  CONTACT_LOGGED: "Контакт записан",
  PROMISE_ADDED: "Обещание добавлено",
  DOCUMENT_UPLOADED: "Документ загружен",
  REASSIGN: "Перераспределение",
  SETTING_UPDATED: "Настройка изменена",
  BULK_IMPORT: "Массовый импорт",
  CHANGE_PASSWORD: "Смена пароля",
  DEACTIVATE: "Деактивация",
  PROFIT_PERIOD_APPROVED: "Распределение прибыли утверждено",
};

const ACTION_COLORS: Record<string, string> = {
  CREATE: "bg-green-100 text-green-800",
  UPDATE: "bg-blue-100 text-blue-800",
  DELETE: "bg-red-100 text-red-800",
  LOGIN: "bg-purple-100 text-purple-800",
  LOGOUT: "bg-gray-100 text-gray-700",
  DEAL_APPROVED: "bg-green-100 text-green-800",
  DEAL_REJECTED: "bg-red-100 text-red-800",
  PROFIT_PERIOD_APPROVED: "bg-green-100 text-green-800",
  PAYMENT_RECORDED: "bg-emerald-100 text-emerald-800",
  PAYMENT_CONFIRMED: "bg-emerald-100 text-emerald-800",
};

const ENTITY_LABELS: Record<string, string> = {
  users: "Сотрудники",
  clients: "Клиенты",
  deals: "Сделки",
  deal_params: "Параметры сделок",
  payments: "Платежи",
  payment_schedules: "Графики платежей",
  overdue_cases: "Дела СБ",
  contact_logs: "Контакты СБ",
  payment_promises: "Обещания платежей",
  documents: "Документы",
  notifications_log: "Уведомления",
  system_settings: "Настройки",
  staff_notifications: "Уведомления сотрудников",
  investors: "Инвесторы",
  expenses: "Расходы",
  profit_periods: "Распределение прибыли",
  profit_distributions: "Доли инвесторов",
};

const ENTITY_OPTIONS = [
  "users", "clients", "deals", "payments",
  "overdue_cases", "documents", "system_settings",
];

const ACTION_OPTIONS = [
  "CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT",
  "DEAL_APPROVED", "DEAL_REJECTED", "PAYMENT_RECORDED",
  "STATUS_CHANGE", "BULK_IMPORT",
];

const ROLE_RU: Record<string, string> = {
  manager: "Менеджер",
  sb: "Сотрудник СБ",
  director: "Руководитель",
};

const SETTING_KEY_RU: Record<string, string> = {
  red_zone_days: "Красная зона (дней без контакта)",
  murabaha_rate_with_down_pct: "Мурабаха: % в месяц со взносом",
  murabaha_rate_without_down_pct: "Мурабаха: % в месяц без взноса",
  murabaha_rate_auto_pct: "Мурабаха: % в месяц (авто)",
  murabaha_seller_fio: "Мурабаха: ФИО продавца",
  notification_templates: "Шаблоны уведомлений",
  sms_api_key: "SMS.ru — API ключ",
  sms_from: "SMS.ru — отправитель",
  director_email: "Email руководителя",
};

const STATUS_RU: Record<string, string> = {
  draft: "Черновик",
  pending: "На согласовании",
  active: "Активна",
  closed: "Закрыта",
  overdue: "Просрочена",
  new: "Новое",
  in_progress: "В работе",
  agreed: "Договорились",
  verified: "Проверен",
  rejected: "Отклонён",
};

function extractDetail(
  action: string,
  newVal: Record<string, unknown> | null,
  oldVal: Record<string, unknown> | null,
): string | null {
  const n = newVal ?? {};
  const o = oldVal ?? {};

  // Settings change
  if (n.key && typeof n.key === "string") {
    const keyRu = SETTING_KEY_RU[n.key] ?? n.key;
    const val = n.value !== undefined ? String(n.value).slice(0, 30) : "";
    return val ? `${keyRu} → ${val}` : keyRu;
  }

  // New employee created
  if (action === "CREATE" && n.name && n.role) {
    return `${n.name} (${ROLE_RU[String(n.role)] ?? n.role})`;
  }

  // Role/profile change
  if (n.role) return `Роль: ${ROLE_RU[String(n.role)] ?? n.role}`;

  // Client name
  if (n.full_name) return String(n.full_name);

  // Status change
  if (n.status && o.status) {
    const from = STATUS_RU[String(o.status)] ?? o.status;
    const to = STATUS_RU[String(n.status)] ?? n.status;
    return `${from} → ${to}`;
  }
  if (n.status) return STATUS_RU[String(n.status)] ?? String(n.status);

  // Payment
  if (n.amount) return `${n.amount} ₽`;

  // Reassign
  if (action === "REASSIGN") {
    const deals = Array.isArray(n.deal_ids) ? n.deal_ids.length : 0;
    const clients = Array.isArray(n.client_ids) ? n.client_ids.length : 0;
    const parts = [];
    if (deals) parts.push(`${deals} сделок`);
    if (clients) parts.push(`${clients} клиентов`);
    return parts.length ? `Перенесено: ${parts.join(", ")}` : "Перераспределение";
  }

  // Bulk import
  if (n.imported !== undefined) return `Импортировано ${n.imported} клиентов`;

  // Document upload
  if (action === "DOCUMENT_UPLOADED" && n.file_name) return String(n.file_name);

  // Decision comment
  if (n.rejection_comment && typeof n.rejection_comment === "string") {
    return `Причина: ${String(n.rejection_comment).slice(0, 50)}`;
  }
  if (n.comment && typeof n.comment === "string" && n.comment.length > 0) {
    return String(n.comment).slice(0, 50);
  }

  // Deal total
  if (n.total) return `Сумма: ${n.total} ₽`;

  return null;
}

export default function AuditPage() {
  const [entity, setEntity] = useState("");
  const [action, setAction] = useState("");
  const [userId, setUserId] = useState("");
  const [offset, setOffset] = useState(0);

  const { data, isLoading } = useAuditLog({
    entity: entity || undefined,
    action: action || undefined,
    user_id: userId || undefined,
    limit: LIMIT,
    offset,
  });

  const { data: managers } = useManagerControl();

  const exportExcel = async () => {
    const response = await api.post(
      "/api/director/audit/export",
      { entity: entity || undefined, action: action || undefined },
      { responseType: "blob" }
    );
    const url = URL.createObjectURL(response.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = `аудит_${new Date().toISOString().slice(0, 10)}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Shield size={22} className="text-[#1a3a5c]" />
          <h1 className="text-xl font-bold">Журнал аудита</h1>
        </div>
        <Button size="sm" variant="outline" onClick={exportExcel}>
          <Download size={16} /> Скачать Excel
        </Button>
      </div>

      <div className="bg-white rounded-xl border p-4 flex gap-3 flex-wrap">
        <select
          value={userId}
          onChange={(e) => { setUserId(e.target.value); setOffset(0); }}
          className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        >
          <option value="">Все сотрудники</option>
          {(managers as { user_id: string; name: string }[] ?? []).map((m) => (
            <option key={m.user_id} value={m.user_id}>{m.name}</option>
          ))}
        </select>
        <select
          value={action}
          onChange={(e) => { setAction(e.target.value); setOffset(0); }}
          className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        >
          <option value="">Все действия</option>
          {ACTION_OPTIONS.map((a) => (
            <option key={a} value={a}>{ACTION_LABELS[a] ?? a}</option>
          ))}
        </select>
        <select
          value={entity}
          onChange={(e) => { setEntity(e.target.value); setOffset(0); }}
          className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        >
          <option value="">Все разделы</option>
          {ENTITY_OPTIONS.map((e) => (
            <option key={e} value={e}>{ENTITY_LABELS[e] ?? e}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Время</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Сотрудник</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Действие</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Раздел</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">Детали</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden xl:table-cell">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(data?.items as { id: number; action: string; entity: string; entity_id: string | null; created_at: string; ip: string | null; user_name: string | null; new_val: Record<string, unknown> | null; old_val: Record<string, unknown> | null }[] ?? []).map((entry) => {
                  const detail = extractDetail(entry.action, entry.new_val, entry.old_val);

                  return (
                    <tr key={entry.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 text-gray-500 text-xs whitespace-nowrap">{formatDateTime(entry.created_at)}</td>
                      <td className="px-4 py-2.5 font-medium text-[#1a3a5c]">
                        {entry.user_name ?? <span className="text-gray-400 text-xs">Система</span>}
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${ACTION_COLORS[entry.action] ?? "bg-gray-100 text-gray-700"}`}>
                          {ACTION_LABELS[entry.action] ?? entry.action}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-gray-700">{ENTITY_LABELS[entry.entity] ?? entry.entity}</td>
                      <td className="px-4 py-2.5 hidden lg:table-cell text-gray-500 text-xs">
                        {detail ?? <span className="text-gray-300">—</span>}
                      </td>
                      <td className="px-4 py-2.5 hidden xl:table-cell text-gray-400 text-xs">
                        {entry.ip ?? "—"}
                      </td>
                    </tr>
                  );
                })}
                {!data?.items.length && (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-gray-500">Записей нет</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {data && data.total > LIMIT && (
            <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
              <p className="text-sm text-gray-500">{data.total} записей</p>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setOffset(Math.max(0, offset - LIMIT))} disabled={offset === 0}>Назад</Button>
                <Button size="sm" variant="outline" onClick={() => setOffset(offset + LIMIT)} disabled={offset + LIMIT >= data.total}>Далее</Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
