import { z } from "zod";

const positiveDecimal = z
  .string()
  .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, {
    message: "Должно быть положительным числом",
  });

const nonNegativeDecimal = z
  .string()
  .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) >= 0, {
    message: "Должно быть неотрицательным числом",
  });

export const murabahaSchema = z.object({
  principal: positiveDecimal,
  markup: nonNegativeDecimal,
  duration_months: z.coerce.number().int().min(1).max(360),
  start_date: z.string().min(1, "Укажите дату начала"),
});

export const ijaraSchema = z.object({
  monthly_rent: positiveDecimal,
  duration_months: z.coerce.number().int().min(1).max(360),
  start_date: z.string().min(1, "Укажите дату начала"),
  buyout_amount: z.string().optional().nullable(),
});

export const dealCreateSchema = z
  .object({
    client_id: z.string().uuid("Выберите клиента"),
    type: z.enum(["murabaha", "ijara"]),
    product_description: z.string().max(2000).optional().or(z.literal("")),
    murabaha: murabahaSchema.optional(),
    ijara: ijaraSchema.optional(),
  })
  .refine(
    (d) => {
      if (d.type === "murabaha") return !!d.murabaha;
      if (d.type === "ijara") return !!d.ijara;
      return false;
    },
    { message: "Заполните параметры сделки" }
  );

export type DealCreateForm = z.infer<typeof dealCreateSchema>;

export const restructureSchema = z.object({
  reason: z.string().min(10, "Обоснование минимум 10 символов"),
});
export type RestructureForm = z.infer<typeof restructureSchema>;
