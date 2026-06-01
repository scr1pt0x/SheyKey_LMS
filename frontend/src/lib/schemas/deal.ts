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

const murabahaTariff = z.enum([
  "NO_DOWNPAYMENT",
  "NO_GUARANTOR",
  "ONE_GUARANTOR",
  "TWO_GUARANTORS",
]);

const murabahaCategory = z.enum(["consumer", "phones", "auto"]);

const guarantorTariffs = ["ONE_GUARANTOR", "TWO_GUARANTORS"] as const;

export const murabahaSchema = z
  .object({
    product_category: murabahaCategory,
    tariff: murabahaTariff,
    down_payment_pct: z.coerce.number().int().min(0).max(90),
    principal: positiveDecimal,
    markup: nonNegativeDecimal,
    duration_months: z.coerce.number().int().min(1).max(360),
    start_date: z.string().min(1, "Укажите дату начала"),
    item_qty: z.coerce.number().int().min(1).max(999).default(1),
    payday: z.coerce.number().int().min(1).max(28).default(1),
    pledge: z.enum(["Да", "Нет"]).default("Нет"),
    guarantor_name: z.string().optional(),
    guarantor_phone: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    if (guarantorTariffs.includes(data.tariff as (typeof guarantorTariffs)[number])) {
      if (!data.guarantor_name?.trim()) {
        ctx.addIssue({ code: "custom", message: "Укажите ФИО поручителя", path: ["guarantor_name"] });
      }
      if (!data.guarantor_phone?.trim()) {
        ctx.addIssue({ code: "custom", message: "Укажите телефон поручителя", path: ["guarantor_phone"] });
      }
    }
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
