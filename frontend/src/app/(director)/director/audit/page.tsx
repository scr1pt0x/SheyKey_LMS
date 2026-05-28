"use client";

import { useState } from "react";
import { useAuditLog } from "@/hooks/useDirector";
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
  KYC_UPDATE: "Обновление KYC",
  ARCHIVE: "Архивация",
  ADD_NOTE: "Заметка",
  STATUS_CHANGE: "Смена статуса",
  CASE_ASSIGNED: "Дело назначено",
  CONTACT_LOGGED: "Контакт записан",
  PROMISE_ADDED: "Обещание добавлено",
  RESTRUCTURE_REQUEST: "Запрос реструктуризации",
  RESTRUCTURING_APPROVED: "Реструктуризация одобрена",
  RESTRUCTURING_REJECTED: "Реструктуризация отклонена",
  DOCUMENT_UPLOADED: "Документ загружен",
  REASSIGN: "Перераспределение",
  SETTING_UPDATED: "Настройка изменена",
  BULK_IMPORT: "Массовый импорт",
  CHANGE_PASSWORD: "Смена пароля",
  DEACTIVATE: "Деактивация",
};

const ACTION_COLORS: Record<string, string> = {
  CREATE: "bg-green-100 text-green-800",
  UPDATE: "bg-blue-100 text-blue-800",
  DELETE: "bg-red-100 text-red-800",
  LOGIN: "bg-purple-100 text-purple-800",
  LOGOUT: "bg-gray-100 text-gray-700",
  DEAL_APPROVED: "bg-green-100 text-green-800",
  DEAL_REJECTED: "bg-red-100 text-red-800",
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
  restructurings: "Реструктуризации",
  documents: "Документы",
  notifications_log: "Уведомления",
  system_settings: "Настройки",
  staff_notifications: "Уведомления сотрудников",
};

const ENTITY_OPTIONS = [
  "users", "clients", "deals", "payments",
  "overdue_cases", "restructurings", "documents", "system_settings",
];

const ACTION_OPTIONS = [
  "CREATE", "UPDATE", "DELETE", "LOGIN", "LOGOUT",
  "DEAL_APPROVED", "DEAL_REJECTED", "PAYMENT_RECORDED",
  "STATUS_CHANGE", "KYC_UPDATE", "BULK_IMPORT",
];

export default function AuditPage() {
  const [entity, setEntity] = useState("");
  const [action, setAction] = useState("");
  const [offset, setOffset] = useState(0);

  const { data, isLoading } = useAuditLog({
    entity: entity || undefined,
    action: action || undefined,
    limit: LIMIT,
    offset,
  });

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
          <h1 className="text-xl font-bold">Журнал аудита (Шариат)</h1>
        </div>
        <Button size="sm" variant="outline" onClick={exportExcel}>
          <Download size={16} /> Скачать Excel
        </Button>
      </div>

      <div className="bg-white rounded-xl border p-4 flex gap-3 flex-wrap">
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
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Действие</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Раздел</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">ID записи</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">IP</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(data?.items as { id: number; action: string; entity: string; entity_id: string | null; created_at: string; ip: string | null }[] ?? []).map((entry) => (
                  <tr key={entry.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-500 text-xs">{formatDateTime(entry.created_at)}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${ACTION_COLORS[entry.action] ?? "bg-gray-100 text-gray-700"}`}>
                        {ACTION_LABELS[entry.action] ?? entry.action}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-medium">{ENTITY_LABELS[entry.entity] ?? entry.entity}</td>
                    <td className="px-4 py-2.5 hidden md:table-cell text-gray-400 text-xs font-mono">
                      {entry.entity_id?.slice(0, 8) ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 hidden md:table-cell text-gray-500 text-xs">
                      {entry.ip ?? "—"}
                    </td>
                  </tr>
                ))}
                {!data?.items.length && (
                  <tr>
                    <td colSpan={5} className="text-center py-8 text-gray-500">Записей нет</td>
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
