import { z } from "zod";

export const clientCreateSchema = z.object({
  full_name: z.string().min(2, "Минимум 2 символа").max(255),
  phone: z.string().min(7, "Введите телефон").max(20),
  passport: z.string().max(50).optional().nullable(),
  address: z.string().optional().nullable(),
  notes: z.string().optional().nullable(),
  tags: z.array(z.string()).optional(),
});
export type ClientCreateForm = z.infer<typeof clientCreateSchema>;

export const clientUpdateSchema = clientCreateSchema.partial();
export type ClientUpdateForm = z.infer<typeof clientUpdateSchema>;

export const noteSchema = z.object({
  note: z.string().min(1, "Заметка не может быть пустой"),
});
