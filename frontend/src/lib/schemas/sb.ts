import { z } from "zod";

export const contactLogSchema = z.object({
  type: z.enum(["call", "meeting", "sms", "telegram", "other"]),
  result: z.string().min(1, "Укажите результат"),
  next_action: z.string().optional().nullable(),
  next_action_date: z.string().optional().nullable(),
});
export type ContactLogForm = z.infer<typeof contactLogSchema>;

export const paymentPromiseSchema = z.object({
  promised_date: z.string().min(1, "Укажите дату"),
  promised_amount: z
    .string()
    .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, {
      message: "Введите сумму",
    }),
});
export type PaymentPromiseForm = z.infer<typeof paymentPromiseSchema>;

export const restructureRequestSchema = z.object({
  reason: z.string().min(10, "Минимум 10 символов"),
});

export const decisionSchema = z.object({
  comment: z.string().min(1, "Укажите комментарий"),
});
