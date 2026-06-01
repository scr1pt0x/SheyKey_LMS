"use client";

import { useState, useEffect } from "react";
import { useForm, type FieldErrors } from "react-hook-form";
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
import { useStaffUsers } from "@/hooks/useDirector";
import { useAuthStore } from "@/store/auth";
import { MurabahaDealFields } from "@/components/features/manager/MurabahaDealFields";

type DealType = "murabaha" | "ijara";

function firstFormErrorMessage(errors: FieldErrors<DealCreateForm>): string | undefined {
  const walk = (obj: Record<string, unknown>): string | undefined => {
    for (const val of Object.values(obj)) {
      if (!val || typeof val !== "object") continue;
      if ("message" in val && typeof (val as { message?: unknown }).message === "string") {
        return (val as { message: string }).message;
      }
      const nested = walk(val as Record<string, unknown>);
      if (nested) return nested;
    }
    return undefined;
  };
  return walk(errors as Record<string, unknown>);
}

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
  const [responsibleManagerId, setResponsibleManagerId] = useState("");
  const user = useAuthStore((s) => s.user);
  const isDirector = user?.role === "director";
  const { data: clientsData } = useClients({
    scope: "all",
    limit: 100,
    is_archived: false,
  });
  const { data: managers = [] } = useStaffUsers("manager", {
    enabled: !!isDirector,
  });
  const createDeal = useCreateDeal();

  const { register, handleSubmit, setValue, formState: { errors } } = useForm<DealCreateForm>({
    resolver: zodResolver(dealCreateSchema),
    defaultValues: {
      type: "murabaha",
      client_id: preselectedClientId,
      murabaha: {
        product_category: "consumer",
        tariff: "ONE_GUARANTOR",
        down_payment_pct: 20,
        principal: "",
        markup: "",
        duration_months: 6,
        start_date: "",
        item_qty: 1,
        payday: 1,
        pledge: "Нет",
        guarantor_name: "",
        guarantor_phone: "",
      },
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
    const product = data.product_description?.trim();
    if (product) payload.product_description = product;
    if (responsibleManagerId) {
      payload.responsible_manager_id = responsibleManagerId;
    }

    if (data.type === "murabaha" && data.murabaha) {
      payload.murabaha = {
        product_category: data.murabaha.product_category,
        tariff: data.murabaha.tariff,
        down_payment_pct: data.murabaha.down_payment_pct,
        principal: data.murabaha.principal,
        markup: data.murabaha.markup,
        duration_months: data.murabaha.duration_months,
        start_date: data.murabaha.start_date,
        item_qty: data.murabaha.item_qty,
        payday: data.murabaha.payday,
        pledge: data.murabaha.pledge,
        guarantor_name: data.murabaha.guarantor_name?.trim() || undefined,
        guarantor_phone: data.murabaha.guarantor_phone?.trim() || undefined,
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
    <div className="w-full max-w-4xl space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/deals">
          <Button variant="ghost" size="icon"><ArrowLeft size={20} /></Button>
        </Link>
        <h1 className="text-xl font-bold">Новая сделка</h1>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit, (invalid) => {
          const msg = firstFormErrorMessage(invalid) ?? "Проверьте обязательные поля формы";
          toast({ title: "Не удалось создать сделку", description: msg, variant: "destructive" });
        })}
        className="bg-white rounded-xl border p-6 space-y-5"
      >
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

        {isDirector && (
          <Field label="Ответственный менеджер">
            <select
              value={responsibleManagerId}
              onChange={(e) => setResponsibleManagerId(e.target.value)}
              className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            >
              <option value="">Не назначать (остаётся у руководителя)</option>
              {managers
                .filter((m) => m.is_active)
                .map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
            </select>
          </Field>
        )}

        <Field label="Что купил (товар / предмет сделки)" error={errors.product_description?.message}>
          <input
            {...register("product_description")}
            type="text"
            placeholder="Например: iPhone 15, холодильник Samsung"
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          />
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
          <MurabahaDealFields register={register} setValue={setValue} errors={errors} />
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
