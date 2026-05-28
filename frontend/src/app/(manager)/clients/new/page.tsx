"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useCreateClient } from "@/hooks/useClients";
import { clientCreateSchema, ClientCreateForm } from "@/lib/schemas/client";
import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/lib/axios";
import { toast } from "@/hooks/useToast";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function NewClientPage() {
  const router = useRouter();
  const createClient = useCreateClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ClientCreateForm>({ resolver: zodResolver(clientCreateSchema) });

  const onSubmit = (data: ClientCreateForm) => {
    createClient.mutate(data, {
      onSuccess: (client) => {
        toast({ title: "Клиент создан", description: client.full_name });
        router.push(`/clients/${client.id}`);
      },
      onError: (err) => {
        toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" });
      },
    });
  };

  return (
    <div className="max-w-xl space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/clients">
          <Button variant="ghost" size="icon">
            <ArrowLeft size={20} />
          </Button>
        </Link>
        <h1 className="text-xl font-bold">Новый клиент</h1>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-xl border p-6 space-y-5">
        <Field label="ФИО *" error={errors.full_name?.message}>
          <input
            {...register("full_name")}
            placeholder="Иванов Иван Иванович"
            className="input"
          />
        </Field>
        <Field label="Телефон *" error={errors.phone?.message}>
          <input
            {...register("phone")}
            type="tel"
            placeholder="+79001234567"
            className="input"
          />
        </Field>
        <Field label="Паспорт" error={errors.passport?.message}>
          <input
            {...register("passport")}
            placeholder="1234 567890"
            className="input"
          />
        </Field>
        <Field label="Адрес" error={errors.address?.message}>
          <textarea
            {...register("address")}
            rows={2}
            placeholder="г. Москва, ул. Примерная, д. 1"
            className="input resize-none"
          />
        </Field>
        <Field label="Заметки" error={errors.notes?.message}>
          <textarea
            {...register("notes")}
            rows={3}
            placeholder="Дополнительная информация..."
            className="input resize-none"
          />
        </Field>

        <div className="flex gap-3 pt-2">
          <Button
            type="submit"
            loading={createClient.isPending}
            className="flex-1"
          >
            Создать клиента
          </Button>
          <Link href="/clients">
            <Button type="button" variant="outline">
              Отмена
            </Button>
          </Link>
        </div>
      </form>

      <style jsx>{`
        .input {
          width: 100%;
          padding: 0.625rem 0.75rem;
          font-size: 0.875rem;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          outline: none;
          transition: box-shadow 0.15s;
        }
        .input:focus {
          box-shadow: 0 0 0 2px #1a3a5c40;
          border-color: #1a3a5c;
        }
      `}</style>
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  );
}
