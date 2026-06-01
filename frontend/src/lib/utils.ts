import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";
import { ru } from "date-fns/locale";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  const d = typeof date === "string" ? parseISO(date) : date;
  return format(d, "dd.MM.yyyy", { locale: ru });
}

export function formatDateTime(date: string | Date): string {
  const d = typeof date === "string" ? parseISO(date) : date;
  return format(d, "dd.MM.yyyy HH:mm", { locale: ru });
}

export function formatCurrency(amount: number | string): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 2,
  }).format(num);
}

export function formatPhone(phone: string): string {
  const clean = phone.replace(/\D/g, "");
  if (clean.length === 11) {
    return `+7 (${clean.slice(1, 4)}) ${clean.slice(4, 7)}-${clean.slice(7, 9)}-${clean.slice(9)}`;
  }
  return phone;
}

export const DEAL_TYPE_LABELS: Record<string, string> = {
  murabaha: "Мурабаха",
  ijara: "Иджара",
};

export const DEAL_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  active: "Активна",
  closed: "Закрыта",
  overdue: "Просрочена",
};

export const DEAL_STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  active: "bg-green-100 text-green-800",
  closed: "bg-blue-100 text-blue-700",
  overdue: "bg-red-100 text-red-800",
};

export const OVERDUE_STATUS_LABELS: Record<string, string> = {
  new: "Новое",
  in_progress: "В работе",
  agreed: "Договорились",
  closed: "Закрыто",
};

export const COLLECTION_STAGE_LABELS: Record<number, string> = {
  1: "Этап 1 — менеджер",
  2: "Этап 2 — Шамиль",
  3: "Этап 3 — Усман",
  4: "Этап 4 — Докка",
};

/** Плашка на «Просрочниках»: зона ответственности этого СБ */
export const SB_STAGE_INFO_HINT: Record<number, string> = {
  2: "Ранняя просрочка после менеджера: от 30 дней и 2 неоплаченных платежей. Новые дела появляются здесь и назначаются на вас автоматически.",
  3: "Усиленное взыскание: от 60 дней и 3 неоплаченных платежей. Дела на этом этапе назначаются на вас автоматически.",
  4: "Критичная просрочка: 90 дней и более без погашения. Такие дела назначаются на вас автоматически.",
};

/** Когда на этапе пока нет дел (список / дашборд) */
export const SB_STAGE_EMPTY_HINT: Record<number, string> = {
  2: "Сейчас дел на этапе 2 нет.",
  3: "Сейчас дел на этапе 3 нет.",
  4: "Сейчас дел на этапе 4 нет.",
};

/** Заголовок блока для сотрудника СБ (без имени другого этапа) */
export function sbStageBannerTitle(stage: number): string {
  return `Просрочка, этап ${stage}`;
}

export function sbStageSectionTitle(stage: number): string {
  const label = COLLECTION_STAGE_LABELS[stage] ?? `Этап ${stage}`;
  return `Просрочка, ${label}`;
}

export const PAYMENT_METHOD_LABELS: Record<string, string> = {
  cash: "Наличные",
  transfer: "Перевод",
  card: "Карта",
  other: "Другое",
};

export const CONTACT_TYPE_LABELS: Record<string, string> = {
  call: "Звонок",
  meeting: "Встреча",
  sms: "SMS",
  telegram: "Telegram",
  other: "Другое",
};

export const ROLE_LABELS: Record<string, string> = {
  manager: "Менеджер",
  sb: "Служба Безопасности",
  director: "Руководитель",
};
