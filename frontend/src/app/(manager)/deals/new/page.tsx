"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter, useSearchParams } from "next/navigation";
import { useCreateDeal } from "@/hooks/useDeals";
import { dealCreateSchema, DealCreateForm } from "@/lib/schemas/deal";
import { Button } from "@/components/ui/button";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { DEAL_TYPE_LABELS } from "@/lib/utils";
import { useClients } from "@/hooks/useClients";

type DealType = "murabaha" | "ijara";

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  );
}

export default function NewDealPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedClientId = searchParams.get("client_id") ?? "";

  const [dealType, setDealType] = useState<DealType>("murabaha");
  const { data: clientsData } = useClients({ limit: 100, is_archived: false });
  const createDeal = useCreateDeal();

  const { register, handleSubmit, setValue, formState: { errors } } = useForm<DealCreateForm>({
    resolver: zodResolver(dealCreateSchema),
    defaultValues: {
      type: "murabaha",
      client_id: preselectedClientId,
    },
  });

  useEffect(() => {
    setValue("type", dealType);
  }, [dealType, setValue]);

  const onSubmit = (data: DealCreateForm) => {
    const payload: Record<string, unknown> = {
      client_id: data.client_id,
      type: data.type,
    };

    if (data.type === "murabaha" && data.murabaha) {
      payload.murabaha = {
        principal: data.murabaha.principal,
        markup: data.murabaha.markup,
        duration_months: data.murabaha.duration_months,
        start_date: data.murabaha.start_date,
      };
    } else if (data.type === "ijara" && data.ijara) {
      payload.ijara = data.ijara;
    }

    createDeal.mutate(payload, {
      onSuccess: (deal) => {
        toast({ title: "Сделка создана" });
        router.push(`/deals/${deal.id}`);
      },
      onError: (err) => {
        toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" });
      },
    });
  };

  return (
    <div className="max-w-xl space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/deals">
          <Button variant="ghost" size="icon"><ArrowLeft size={20} /></Button>
        </Link>
        <h1 className="text-xl font-bold">Новая сделка</h1>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="bg-white rounded-xl border p-6 space-y-5">
        {/* Client selector */}
        <Field label="Клиент *" error={errors.client_id?.message}>
          <select
            {...register("client_id")}
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          >
            <option value="">Выберите клиента</option>
            {clientsData?.items.map((c) => (
              <option key={c.id} value={c.id}>{c.full_name} — {c.phone}</option>
            ))}
          </select>
        </Field>

        {/* Deal type */}
        <Field label="Тип сделки *" error={errors.type?.message}>
          <div className="grid grid-cols-3 gap-2">
            {(["murabaha", "ijara"] as DealType[]).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setDealType(t)}
                className={`py-2.5 px-3 text-sm rounded-lg border font-medium transition-colors ${
                  dealType === t
                    ? "bg-[#1a3a5c] text-white border-[#1a3a5c]"
                    : "hover:bg-gray-50 border-gray-200"
                }`}
              >
                {DEAL_TYPE_LABELS[t]}
              </button>
            ))}
          </div>
        </Field>

        {/* Murabaha params */}
        {dealType === "murabaha" && (
          <>
            <Field label="Стоимость товара (₽) *" error={errors.murabaha?.principal?.message}>
              <input {...register("murabaha.principal")} type="number" step="0.01" placeholder="500000" className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
            </Field>
            <Field label="Наценка банка (₽) *" error={errors.murabaha?.markup?.message}>
              <input {...register("murabaha.markup")} type="number" step="0.01" placeholder="75000" className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
            </Field>
            <Field label="Срок (мес.) *" error={errors.murabaha?.duration_months?.message}>
              <input {...register("murabaha.duration_months")} type="number" min="1" max="360" placeholder="24" className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
            </Field>
            <Field label="Дата начала *" error={errors.murabaha?.start_date?.message}>
              <input {...register("murabaha.start_date")} type="date" className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
            </Field>
          </>
        )}

        {/* Ijara params */}
        {dealType === "ijara" && (
          <>
            <Field label="Ежемесячная аренда (₽) *" error={errors.ijara?.monthly_rent?.message}>
              <input {...register("ijara.monthly_rent")} type="number" step="0.01" placeholder="25000" className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
            </Field>
            <Field label="Срок (мес.) *" error={errors.ijara?.duration_months?.message}>
              <input {...register("ijara.duration_months")} type="number" min="1" max="360" placeholder="36" className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
            </Field>
            <Field label="Сумма выкупа (₽, необязательно)" error={errors.ijara?.buyout_amount?.message}>
              <input {...register("ijara.buyout_amount")} type="number" step="0.01" placeholder="100000" className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
            </Field>
            <Field label="Дата начала *" error={errors.ijara?.start_date?.message}>
              <input {...register("ijara.start_date")} type="date" className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
            </Field>
          </>
        )}

        <div className="flex gap-3 pt-2">
          <Button type="submit" loading={createDeal.isPending} className="flex-1">
            Создать сделку
          </Button>
          <Link href="/deals">
            <Button type="button" variant="outline">Отмена</Button>
          </Link>
        </div>
      </form>
    </div>
  );
}
