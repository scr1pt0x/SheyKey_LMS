"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { Settings } from "lucide-react";

const SETTINGS_KEYS = [
  {
    key: "red_zone_days",
    label: "Красная зона: дней без контакта по делу (СБ)",
    hint: "Не этап просрочки и не передача в СБ — только давность последнего контакта с клиентом.",
    type: "number",
    group: "Основные",
  },
  {
    key: "murabaha_rate_with_down_pct",
    label: "Мурабаха: % в месяц со взносом (потребительские, телефоны)",
    type: "number",
    group: "Мурабаха",
  },
  {
    key: "murabaha_rate_without_down_pct",
    label: "Мурабаха: % в месяц без взноса (потребительские, телефоны)",
    type: "number",
    group: "Мурабаха",
  },
  {
    key: "murabaha_rate_auto_pct",
    label: "Мурабаха: % в месяц (авто, только со взносом)",
    type: "number",
    group: "Мурабаха",
  },
  {
    key: "murabaha_seller_fio",
    label: "Мурабаха: ФИО продавца в договоре",
    type: "text",
    group: "Мурабаха",
  },
  { key: "director_email",             label: "Email руководителя (автоотчёты)",           type: "text",    group: "Уведомления" },
  { key: "sms_api_key",                label: "SMS.ru — API ключ",                         type: "text",    group: "Уведомления" },
  { key: "sms_from",                   label: "SMS.ru — Имя отправителя",                  type: "text",    group: "Уведомления" },
  { key: "manager_bonus_pct",          label: "Бонус менеджерам от прибыли (%)",           type: "number",  group: "Прибыль" },
  { key: "debt_stage_2_days",          label: "Этап 2: мин. дней просрочки",               type: "number",  group: "Этапы долга" },
  { key: "debt_stage_2_installments",  label: "Этап 2: мин. просроченных платежей",        type: "number",  group: "Этапы долга" },
  { key: "debt_stage_3_days",          label: "Этап 3: мин. дней просрочки",               type: "number",  group: "Этапы долга" },
  { key: "debt_stage_3_installments",  label: "Этап 3: мин. просроченных платежей",        type: "number",  group: "Этапы долга" },
  { key: "debt_stage_4_days",          label: "Этап 4: мин. дней просрочки",               type: "number",  group: "Этапы долга" },
  { key: "debt_stage_2_sb_user_id",    label: "Этап 2: UUID сотрудника (Шамиль)",          type: "text",    group: "Этапы долга" },
  { key: "debt_stage_3_sb_user_id",    label: "Этап 3: UUID сотрудника (Усман)",           type: "text",    group: "Этапы долга" },
  { key: "debt_stage_4_sb_user_id",    label: "Этап 4: UUID сотрудника (Докка)",           type: "text",    group: "Этапы долга" },
  { key: "manager_payment_commission_pct", label: "% менеджера с оплаты (этапы 1–2)",      type: "number",  group: "Комиссии с оплат" },
  { key: "manager_payment_commission_from_stage_3_pct", label: "% менеджера с оплаты (этап 3+)", type: "number", group: "Комиссии с оплат" },
  { key: "sb_commission_stage_2_pct",  label: "% СБ с оплаты (этап 2)",                    type: "number",  group: "Комиссии с оплат" },
  { key: "sb_commission_stage_3_pct",  label: "% СБ с оплаты (этап 3)",                    type: "number",  group: "Комиссии с оплат" },
  { key: "sb_commission_stage_4_pct",  label: "% СБ с оплаты (этап 4)",                    type: "number",  group: "Комиссии с оплат" },
];

export default function SettingsPage() {
  const qc = useQueryClient();
  const [editValues, setEditValues] = useState<Record<string, string>>({});

  const settingsData = SETTINGS_KEYS.map(({ key }) => {
    return useQuery({
      queryKey: ["settings", key],
      queryFn: async () => {
        const { data } = await api.get(`/api/director/settings/${key}`);
        return data;
      },
    });
  });

  const updateSetting = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string | number }) => {
      await api.patch(`/api/director/settings/${key}`, { value });
    },
    onSuccess: (_d, { key }) => {
      toast({ title: "Настройка сохранена" });
      qc.invalidateQueries({ queryKey: ["settings", key] });
      setEditValues((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    },
    onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Settings size={22} className="text-[#1a3a5c]" />
        <h1 className="text-xl font-bold">Настройки системы</h1>
      </div>

      <div className="bg-white rounded-xl border divide-y">
        {SETTINGS_KEYS.map(({ key, label, type, hint }, idx) => {
          const query = settingsData[idx];
          const currentValue = query.data?.value ?? "";
          const editValue = editValues[key];
          const isEditing = editValue !== undefined;

          return (
            <div key={key} className="p-5 flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm">{label}</p>
                {hint && <p className="text-xs text-gray-500 mt-0.5">{hint}</p>}
                <p className="text-xs text-gray-400 font-mono">{key}</p>
              </div>
              <div className="flex items-center gap-3">
                {isEditing ? (
                  <>
                    <input
                      type={key === "sms_api_key" ? "password" : type}
                      value={editValue}
                      onChange={(e) =>
                        setEditValues((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      className="w-48 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                    />
                    <Button
                      size="sm"
                      loading={updateSetting.isPending}
                      onClick={() =>
                        updateSetting.mutate({
                          key,
                          value: type === "number" ? parseFloat(editValue) : editValue,
                        })
                      }
                    >
                      Сохранить
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() =>
                        setEditValues((prev) => {
                          const next = { ...prev };
                          delete next[key];
                          return next;
                        })
                      }
                    >
                      ✕
                    </Button>
                  </>
                ) : (
                  <>
                    <span className="font-semibold text-[#1a3a5c]">
                      {query.isLoading
                        ? "..."
                        : key === "sms_api_key" && currentValue
                        ? "••••••••" + String(currentValue).slice(-4)
                        : String(currentValue ?? "—")}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setEditValues((prev) => ({ ...prev, [key]: String(currentValue ?? "") }))
                      }
                    >
                      Изменить
                    </Button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
