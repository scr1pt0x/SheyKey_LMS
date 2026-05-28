import { z } from "zod";

export const paymentCreateSchema = z.object({
  schedule_id: z.string().uuid("Выберите строку графика"),
  amount: z
    .string()
    .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, {
      message: "Сумма должна быть положительной",
    }),
  paid_at: z.string().min(1, "Укажите дату"),
  method: z.enum(["cash", "transfer", "card", "other"]),
  notes: z.string().optional().nullable(),
});
export type PaymentCreateForm = z.infer<typeof paymentCreateSchema>;
