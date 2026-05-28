import { z } from "zod";

export const loginSchema = z.object({
  phone: z.string().min(7, "Введите номер телефона"),
  password: z.string().min(1, "Введите пароль"),
});
export type LoginForm = z.infer<typeof loginSchema>;

export const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Введите текущий пароль"),
    new_password: z.string().min(8, "Минимум 8 символов"),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Пароли не совпадают",
    path: ["confirm_password"],
  });
export type ChangePasswordForm = z.infer<typeof changePasswordSchema>;
