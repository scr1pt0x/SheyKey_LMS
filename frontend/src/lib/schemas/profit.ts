import { z } from "zod";

export const expenseCategorySchema = z.enum([
  "cost_of_goods",
  "operational",
  "salary",
  "rent",
  "other",
]);

export const investorCreateSchema = z.object({
  name: z.string().min(2, "Минимум 2 символа"),
  phone: z.string().max(20).optional().nullable(),
  investment_amount: z
    .number({ invalid_type_error: "Укажите сумму вложения" })
    .positive("Сумма вложения должна быть больше 0"),
  joined_at: z.string().optional().nullable(),
  notes: z.string().max(2000).optional().nullable(),
});
export type InvestorCreateForm = z.infer<typeof investorCreateSchema>;

export const investorUpdateSchema = z.object({
  name: z.string().min(2).optional(),
  phone: z.string().max(20).optional().nullable(),
  investment_amount: z.number().positive("Сумма вложения должна быть больше 0").optional(),
  joined_at: z.string().optional().nullable(),
  notes: z.string().max(2000).optional().nullable(),
});
export type InvestorUpdateForm = z.infer<typeof investorUpdateSchema>;

export const expenseCreateSchema = z.object({
  category: expenseCategorySchema,
  amount: z
    .number({ invalid_type_error: "Укажите сумму" })
    .positive("Сумма должна быть больше 0"),
  description: z.string().max(500).optional(),
  expense_date: z.string().min(1, "Укажите дату"),
});
export type ExpenseCreateForm = z.infer<typeof expenseCreateSchema>;

export const profitCalculateSchema = z
  .object({
    period_start: z.string().min(1, "Укажите дату начала"),
    period_end: z.string().min(1, "Укажите дату окончания"),
  })
  .refine((d) => d.period_end >= d.period_start, {
    message: "Дата окончания должна быть не раньше даты начала",
    path: ["period_end"],
  });
export type ProfitCalculateForm = z.infer<typeof profitCalculateSchema>;

export const distributionItemSchema = z.object({
  investor_id: z.string().uuid(),
  investor_name: z.string(),
  share_pct: z.number(),
  amount: z.number(),
});
export type DistributionItem = z.infer<typeof distributionItemSchema>;

export const profitPeriodSchema = z.object({
  id: z.string().uuid(),
  period_start: z.string(),
  period_end: z.string(),
  status: z.enum(["draft", "approved"]),
  gross_revenue: z.number(),
  total_expenses: z.number(),
  manager_bonus_pct: z.number(),
  manager_bonus_amount: z.number(),
  net_distributable: z.number(),
  partner_remainder: z.number(),
  distributions: z.array(distributionItemSchema),
  approved_at: z.string().nullable(),
  created_at: z.string(),
});
export type ProfitPeriod = z.infer<typeof profitPeriodSchema>;

export const investorSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  phone: z.string().nullable(),
  share_pct: z.number(),
  investment_amount: z.number().nullable(),
  joined_at: z.string().nullable(),
  notes: z.string().nullable(),
  is_active: z.boolean(),
  created_at: z.string(),
});
export type Investor = z.infer<typeof investorSchema>;

export const investorSummarySchema = z.object({
  total_investors: z.number(),
  total_share_pct: z.number(),
  partner_remainder_pct: z.number(),
  total_invested: z.number(),
});
export type InvestorSummary = z.infer<typeof investorSummarySchema>;

export const expenseSchema = z.object({
  id: z.string().uuid(),
  period_id: z.string().uuid().nullable(),
  category: z.string(),
  category_label: z.string(),
  amount: z.number(),
  description: z.string().nullable(),
  expense_date: z.string(),
  created_at: z.string(),
});
export type Expense = z.infer<typeof expenseSchema>;
