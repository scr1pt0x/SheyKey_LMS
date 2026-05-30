"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import api from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { ROLE_LABELS, formatPhone } from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { User } from "lucide-react";

export default function ProfilePage() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const { data: me, isLoading } = useQuery({
    queryKey: ["auth-me"],
    queryFn: async () => {
      const { data } = await api.get("/api/auth/me");
      return data as { id: string; name: string; role: string; phone: string | null };
    },
  });

  const changePassword = useMutation({
    mutationFn: () =>
      api.post("/api/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      }),
    onSuccess: () => {
      toast({ title: "Пароль изменён", description: "Войдите снова с новым паролем" });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    },
    onError: (err) =>
      toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
  });

  function handlePasswordSubmit() {
    if (newPassword !== confirmPassword) {
      toast({ title: "Пароли не совпадают", variant: "destructive" });
      return;
    }
    if (newPassword.length < 8) {
      toast({ title: "Новый пароль — минимум 8 символов", variant: "destructive" });
      return;
    }
    changePassword.mutate();
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-md">
      <h1 className="text-xl font-bold flex items-center gap-2">
        <User size={22} className="text-[#1a3a5c]" /> Профиль
      </h1>

      <div className="bg-white rounded-xl border p-5 space-y-2">
        <p className="text-sm text-gray-500">Имя</p>
        <p className="font-semibold">{me?.name}</p>
        <p className="text-sm text-gray-500 mt-2">Роль</p>
        <p className="font-medium">{ROLE_LABELS[me?.role ?? ""] ?? me?.role}</p>
        {me?.phone && (
          <>
            <p className="text-sm text-gray-500 mt-2">Телефон (логин)</p>
            <p className="font-medium">{formatPhone(me.phone)}</p>
          </>
        )}
      </div>

      <div className="bg-white rounded-xl border p-5 space-y-4">
        <h2 className="font-semibold">Сменить пароль</h2>
        <div>
          <label className="block text-sm font-medium mb-1">Текущий пароль</label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Новый пароль</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Повторите новый пароль</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          />
        </div>
        <Button size="sm" loading={changePassword.isPending} onClick={handlePasswordSubmit}>
          Сохранить пароль
        </Button>
      </div>
    </div>
  );
}
