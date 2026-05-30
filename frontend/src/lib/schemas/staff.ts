import { z } from "zod";

export const staffCreateSchema = z.object({
  name: z.string().min(2, "Имя — минимум 2 символа").max(255),
  phone: z.string().min(7, "Укажите телефон").max(20),
  role: z.enum(["manager", "sb"], { required_error: "Выберите роль" }),
  password: z.string().min(8, "Пароль — минимум 8 символов"),
});

export const staffUpdateSchema = z.object({
  name: z.string().min(2).max(255).optional(),
  phone: z.string().min(7).max(20).optional(),
  is_active: z.boolean().optional(),
});

export type StaffCreateForm = z.infer<typeof staffCreateSchema>;
