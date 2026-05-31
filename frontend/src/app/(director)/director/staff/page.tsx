"use client";

import { useState } from "react";
import {
  useStaffUsers,
  useCreateStaffUser,
  useUpdateStaffUser,
  useDeactivateStaffUser,
  type StaffUser,
} from "@/hooks/useDirector";
import { staffCreateSchema, staffUpdateSchema } from "@/lib/schemas/staff";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDateTime, formatPhone, ROLE_LABELS } from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { UserPlus, Users, Pencil, X } from "lucide-react";

type RoleFilter = "all" | "manager" | "sb";

type CreateStaffForm = {
  name: string;
  phone: string;
  role: "manager" | "sb";
  password: string;
  passwordConfirm: string;
};

const EMPTY_CREATE: CreateStaffForm = {
  name: "",
  phone: "",
  role: "manager",
  password: "",
  passwordConfirm: "",
};

const EMPTY_EDIT = {
  name: "",
  phone: "",
};

export default function StaffPage() {
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [showForm, setShowForm] = useState(false);
  const [editUser, setEditUser] = useState<StaffUser | null>(null);
  const [createForm, setCreateForm] = useState<CreateStaffForm>(EMPTY_CREATE);
  const [editForm, setEditForm] = useState(EMPTY_EDIT);

  const listRole = roleFilter === "all" ? undefined : roleFilter;
  const { data: users = [], isLoading } = useStaffUsers(listRole);
  const createUser = useCreateStaffUser();
  const updateUser = useUpdateStaffUser();
  const deactivateUser = useDeactivateStaffUser();

  function openCreate() {
    setEditUser(null);
    setCreateForm(EMPTY_CREATE);
    setShowForm(true);
  }

  function openEdit(u: StaffUser) {
    setEditUser(u);
    setEditForm({ name: u.name, phone: u.phone ?? "" });
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditUser(null);
  }

  function handleCreate() {
    if (createForm.password !== createForm.passwordConfirm) {
      toast({ title: "Пароли не совпадают", variant: "destructive" });
      return;
    }
    const parsed = staffCreateSchema.safeParse({
      name: createForm.name.trim(),
      phone: createForm.phone.trim(),
      role: createForm.role,
      password: createForm.password,
    });
    if (!parsed.success) {
      toast({
        title: "Проверьте форму",
        description: parsed.error.errors[0]?.message,
        variant: "destructive",
      });
      return;
    }
    createUser.mutate(parsed.data, {
      onSuccess: () => {
        toast({ title: "Сотрудник создан", description: "Передайте ему телефон и пароль для входа" });
        closeForm();
      },
      onError: (err) =>
        toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
    });
  }

  function handleUpdate() {
    if (!editUser) return;
    const parsed = staffUpdateSchema.safeParse({
      name: editForm.name.trim(),
      phone: editForm.phone.trim(),
    });
    if (!parsed.success) {
      toast({
        title: "Проверьте форму",
        description: parsed.error.errors[0]?.message,
        variant: "destructive",
      });
      return;
    }
    updateUser.mutate(
      { userId: editUser.id, ...parsed.data },
      {
        onSuccess: () => {
          toast({ title: "Данные обновлены" });
          closeForm();
        },
        onError: (err) =>
          toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
      }
    );
  }

  function handleDeactivate(u: StaffUser) {
    if (!confirm(`Деактивировать ${u.name}? Вход в систему будет закрыт.`)) return;
    deactivateUser.mutate(u.id, {
      onSuccess: () => toast({ title: "Сотрудник деактивирован" }),
      onError: (err) =>
        toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
    });
  }

  function handleReactivate(u: StaffUser) {
    updateUser.mutate(
      { userId: u.id, is_active: true },
      {
        onSuccess: () => toast({ title: "Сотрудник снова активен" }),
        onError: (err) =>
          toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
      }
    );
  }

  return (
    <div className="space-y-5 w-full">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Users size={22} className="text-[#1a3a5c]" />
          <h1 className="text-xl font-bold">Сотрудники</h1>
        </div>
        <Button size="sm" onClick={openCreate}>
          <UserPlus size={16} /> Добавить
        </Button>
      </div>

      <p className="text-sm text-gray-500">
        Создавайте учётные записи менеджеров и сотрудников СБ. Для входа используются телефон и пароль.
      </p>

      <div className="flex gap-2 flex-wrap">
        {(
          [
            ["all", "Все"],
            ["manager", "Менеджеры"],
            ["sb", "СБ"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            onClick={() => setRoleFilter(value)}
            className={`px-3 py-1.5 text-sm rounded-lg border transition-colors ${
              roleFilter === value
                ? "bg-[#1a3a5c] text-white border-[#1a3a5c]"
                : "bg-white text-gray-600 hover:bg-gray-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">
              {editUser ? "Редактировать сотрудника" : "Новый сотрудник"}
            </h2>
            <button type="button" onClick={closeForm} className="text-gray-400 hover:text-gray-600">
              <X size={20} />
            </button>
          </div>

          {editUser ? (
            <>
              <div>
                <label className="block text-sm font-medium mb-1">Имя</label>
                <input
                  value={editForm.name}
                  onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Телефон</label>
                <input
                  type="tel"
                  value={editForm.phone}
                  onChange={(e) => setEditForm((f) => ({ ...f, phone: e.target.value }))}
                  placeholder="+79001234567"
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                />
              </div>
              <p className="text-xs text-gray-500">
                Роль: {ROLE_LABELS[editUser.role]} (не меняется)
              </p>
              <div className="flex gap-2">
                <Button size="sm" loading={updateUser.isPending} onClick={handleUpdate}>
                  Сохранить
                </Button>
                <Button size="sm" variant="outline" onClick={closeForm}>
                  Отмена
                </Button>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium mb-1">Имя</label>
                <input
                  value={createForm.name}
                  onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Иван Иванов"
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Телефон (логин)</label>
                <input
                  type="tel"
                  value={createForm.phone}
                  onChange={(e) => setCreateForm((f) => ({ ...f, phone: e.target.value }))}
                  placeholder="+79001234567"
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Роль</label>
                <select
                  value={createForm.role}
                  onChange={(e) =>
                    setCreateForm((f) => ({
                      ...f,
                      role: e.target.value as "manager" | "sb",
                    }))
                  }
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                >
                  <option value="manager">Менеджер</option>
                  <option value="sb">Служба Безопасности</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Пароль</label>
                <input
                  type="password"
                  value={createForm.password}
                  onChange={(e) => setCreateForm((f) => ({ ...f, password: e.target.value }))}
                  autoComplete="new-password"
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Повторите пароль</label>
                <input
                  type="password"
                  value={createForm.passwordConfirm}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, passwordConfirm: e.target.value }))
                  }
                  autoComplete="new-password"
                  className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
                />
              </div>
              <div className="flex gap-2">
                <Button size="sm" loading={createUser.isPending} onClick={handleCreate}>
                  Создать
                </Button>
                <Button size="sm" variant="outline" onClick={closeForm}>
                  Отмена
                </Button>
              </div>
            </>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : (
        <div className="bg-white rounded-xl border divide-y">
          {users.length === 0 ? (
            <p className="p-8 text-center text-gray-500 text-sm">Сотрудников нет</p>
          ) : (
            users.map((u) => (
              <div
                key={u.id}
                className="p-4 flex flex-col sm:flex-row sm:items-center gap-3 justify-between"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold">{u.name}</p>
                    <Badge className="bg-gray-100 text-gray-700">{ROLE_LABELS[u.role] ?? u.role}</Badge>
                    {!u.is_active && (
                      <Badge className="bg-gray-100 text-gray-600">Неактивен</Badge>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mt-0.5">
                    {u.phone ? formatPhone(u.phone) : "—"}
                  </p>
                  {u.last_login && (
                    <p className="text-xs text-gray-400 mt-0.5">
                      Последний вход: {formatDateTime(u.last_login)}
                    </p>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" variant="outline" onClick={() => openEdit(u)}>
                    <Pencil size={14} />
                  </Button>
                  {u.is_active ? (
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-red-600 border-red-200"
                      loading={deactivateUser.isPending}
                      onClick={() => handleDeactivate(u)}
                    >
                      Деактивировать
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      loading={updateUser.isPending}
                      onClick={() => handleReactivate(u)}
                    >
                      Активировать
                    </Button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
