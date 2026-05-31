"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api, { getErrorMessage } from "@/lib/axios";
import { loginSchema, LoginForm } from "@/lib/schemas/auth";
import { useAuthStore } from "@/store/auth";
import type { UserRole } from "@/store/auth";

import { ROLE_HOME } from "@/lib/roleHome";

export default function LoginPage() {
  const router = useRouter();
  const setUser = useAuthStore((s) => s.setUser);

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const { mutate: login, isPending } = useMutation({
    mutationFn: async (data: LoginForm) => {
      const res = await api.post("/api/auth/login", data);
      return res.data as { id: string; name: string; role: UserRole };
    },
    onSuccess: (data) => {
      setUser({ id: data.id, name: data.name, role: data.role });
      router.replace(ROLE_HOME[data.role]);
    },
    onError: (err) => {
      setError("password", { message: getErrorMessage(err) });
    },
  });

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#0f2744] to-[#1a3a5c] p-4">
      <div className="w-full max-w-sm">
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-[#1a3a5c]">SheyKey Islamic Finance LMS</h1>
            <p className="text-sm text-gray-500 mt-1">Система управления сделками</p>
          </div>

          <form onSubmit={handleSubmit((d) => login(d))} className="space-y-5">
            <div>
              <label
                htmlFor="phone"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Телефон
              </label>
              <input
                id="phone"
                type="tel"
                autoComplete="tel"
                placeholder="+79001234567"
                {...register("phone")}
                className="w-full px-3 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1a3a5c] text-sm"
              />
              {errors.phone && (
                <p className="text-red-500 text-xs mt-1">{errors.phone.message}</p>
              )}
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Пароль
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register("password")}
                className="w-full px-3 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-[#1a3a5c] text-sm"
              />
              {errors.password && (
                <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isPending}
              className="w-full bg-[#1a3a5c] hover:bg-[#0f2744] text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending ? "Входим..." : "Войти"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
