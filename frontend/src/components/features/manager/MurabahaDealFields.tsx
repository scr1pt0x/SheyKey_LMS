"use client";

import { useEffect, useMemo, useState } from "react";
import type { UseFormRegister, UseFormSetValue, FieldErrors } from "react-hook-form";
import { useMurabahaQuote, useMurabahaTariffOptions } from "@/hooks/useDeals";
import type { DealCreateForm } from "@/lib/schemas/deal";
import {
  MURABAHA_CATEGORY_LABELS,
  MURABAHA_TARIFF_LABELS,
  type MurabahaCategory,
  type MurabahaTariffKey,
} from "@/lib/murabaha";
import { formatCurrency } from "@/lib/utils";

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

type Props = {
  register: UseFormRegister<DealCreateForm>;
  setValue: UseFormSetValue<DealCreateForm>;
  errors: FieldErrors<DealCreateForm>;
};

export function MurabahaDealFields({ register, setValue, errors }: Props) {
  const [category, setCategory] = useState<MurabahaCategory>("consumer");
  const [amount, setAmount] = useState("50000");
  const [term, setTerm] = useState(6);
  const [tariff, setTariff] = useState<MurabahaTariffKey>("ONE_GUARANTOR");
  const [downPct, setDownPct] = useState(20);
  const [itemQty, setItemQty] = useState(1);
  const [payday, setPayday] = useState(1);
  const [pledge, setPledge] = useState<"Да" | "Нет">("Нет");

  const needsGuarantor =
    tariff === "ONE_GUARANTOR" || tariff === "TWO_GUARANTORS";

  const amountNum = parseFloat(amount) || 0;
  const { data: tariffOptions } = useMurabahaTariffOptions(category, amountNum);

  useEffect(() => {
    setValue("murabaha.product_category", category);
  }, [category, setValue]);

  useEffect(() => {
    if (amountNum > 0) {
      setValue("murabaha.principal", amount, { shouldValidate: true });
    }
  }, [amount, amountNum, setValue]);

  useEffect(() => {
    setValue("murabaha.duration_months", term, { shouldValidate: true });
  }, [term, setValue]);

  useEffect(() => {
    if (!tariffOptions) return;
    if (term < tariffOptions.terms_min || term > tariffOptions.terms_max) {
      setTerm(tariffOptions.terms_min);
      setValue("murabaha.duration_months", tariffOptions.terms_min);
    }
    const enabled = tariffOptions.tariffs.filter((t) => t.enabled);
    if (!enabled.some((t) => t.key === tariff) && tariffOptions.default_tariff) {
      setTariff(tariffOptions.default_tariff as MurabahaTariffKey);
      setValue("murabaha.tariff", tariffOptions.default_tariff as MurabahaTariffKey);
    }
  }, [tariffOptions, term, tariff, setValue]);

  useEffect(() => {
    setValue("murabaha.tariff", tariff);
    setValue("murabaha.item_qty", itemQty);
    setValue("murabaha.payday", payday);
    setValue("murabaha.pledge", pledge);
  }, [tariff, itemQty, payday, pledge, setValue]);

  useEffect(() => {
    if (tariff === "NO_DOWNPAYMENT") {
      setDownPct(0);
      setValue("murabaha.down_payment_pct", 0);
    } else if (tariffOptions) {
      const minDown = term > 6 ? 25 : 20;
      if (downPct < minDown) {
        setDownPct(minDown);
        setValue("murabaha.down_payment_pct", minDown);
      }
    }
  }, [tariff, term, tariffOptions, downPct, setValue]);

  const quoteParams = useMemo(() => {
    if (amountNum <= 0 || term <= 0 || !tariff) return null;
    return {
      category,
      amount: amountNum,
      term,
      tariff,
      down_pct: downPct,
    };
  }, [category, amountNum, term, tariff, downPct]);

  const { data: quote, isFetching: quoteLoading } = useMurabahaQuote(quoteParams);

  useEffect(() => {
    if (!quote) return;
    setValue("murabaha.principal", String(quote.principal), { shouldValidate: true });
    setValue("murabaha.markup", String(quote.markup), { shouldValidate: true });
    setValue("murabaha.duration_months", quote.duration_months, { shouldValidate: true });
    setValue("murabaha.down_payment_pct", quote.down_payment_pct, { shouldValidate: true });
  }, [quote, setValue]);

  const termOptions = useMemo(() => {
    if (!tariffOptions) return [];
    const opts: number[] = [];
    for (let m = tariffOptions.terms_min; m <= tariffOptions.terms_max; m++) opts.push(m);
    return opts;
  }, [tariffOptions]);

  const minDown = tariff === "NO_DOWNPAYMENT" ? 0 : term > 6 ? 25 : 20;

  return (
    <>
      <input type="hidden" {...register("murabaha.product_category")} />
      <input type="hidden" {...register("murabaha.tariff")} />
      <input type="hidden" {...register("murabaha.down_payment_pct")} />
      <input type="hidden" {...register("murabaha.principal")} />
      <input type="hidden" {...register("murabaha.markup")} />
      <input type="hidden" {...register("murabaha.duration_months")} />
      <input type="hidden" {...register("murabaha.item_qty")} />
      <input type="hidden" {...register("murabaha.payday")} />
      <input type="hidden" {...register("murabaha.pledge")} />

      <Field label="Категория товара *">
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as MurabahaCategory)}
          className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        >
          {(Object.keys(MURABAHA_CATEGORY_LABELS) as MurabahaCategory[]).map((c) => (
            <option key={c} value={c}>
              {MURABAHA_CATEGORY_LABELS[c]}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Стоимость товара (₽) *" error={errors.murabaha?.principal?.message}>
        <input
          type="number"
          step="1"
          min={1}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        />
      </Field>

      <Field label="Тариф условий *">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {tariffOptions?.tariffs.map((t) => (
            <button
              key={t.key}
              type="button"
              disabled={!t.enabled}
              onClick={() => {
                setTariff(t.key as MurabahaTariffKey);
                setValue("murabaha.tariff", t.key as MurabahaTariffKey);
              }}
              className={`text-left p-3 rounded-lg border text-sm transition-colors ${
                tariff === t.key
                  ? "bg-[#1a3a5c] text-white border-[#1a3a5c]"
                  : t.enabled
                    ? "hover:bg-gray-50 border-gray-200"
                    : "opacity-40 cursor-not-allowed border-gray-100"
              }`}
            >
              <div className="font-medium">{MURABAHA_TARIFF_LABELS[t.key as MurabahaTariffKey] ?? t.label}</div>
              <div className={`text-xs mt-0.5 ${tariff === t.key ? "text-white/80" : "text-gray-500"}`}>
                {formatCurrency(t.amount_min)} – {formatCurrency(t.amount_max)}
              </div>
            </button>
          ))}
        </div>
        {tariffOptions?.special_requirements.map((req) => (
          <p key={req} className="text-xs text-amber-700 mt-2">
            {req}
          </p>
        ))}
      </Field>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Срок (мес.) *" error={errors.murabaha?.duration_months?.message}>
          <select
            value={term}
            onChange={(e) => {
              const v = Number(e.target.value);
              setTerm(v);
              setValue("murabaha.duration_months", v);
            }}
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          >
            {termOptions.map((m) => (
              <option key={m} value={m}>
                {m} мес.
              </option>
            ))}
          </select>
        </Field>

        <Field label={`Первоначальный взнос (%)${tariff !== "NO_DOWNPAYMENT" ? " *" : ""}`}>
          <input
            type="number"
            min={minDown}
            max={90}
            disabled={tariff === "NO_DOWNPAYMENT"}
            value={downPct}
            onChange={(e) => {
              const v = Number(e.target.value);
              setDownPct(v);
              setValue("murabaha.down_payment_pct", v);
            }}
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c] disabled:bg-gray-100"
          />
          <p className="text-xs text-gray-500 mt-1">
            {tariff === "NO_DOWNPAYMENT"
              ? "Фиксировано: 0%"
              : `Мин. ${minDown}% · макс. 90%`}
          </p>
        </Field>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Field label="Количество товара *" error={errors.murabaha?.item_qty?.message}>
          <input
            type="number"
            min={1}
            max={999}
            value={itemQty}
            onChange={(e) => {
              const v = Math.max(1, Number(e.target.value) || 1);
              setItemQty(v);
              setValue("murabaha.item_qty", v);
            }}
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          />
        </Field>

        <Field label="Дата начала *" error={errors.murabaha?.start_date?.message}>
          <input
            {...register("murabaha.start_date", {
              onChange: (e) => {
                const v = e.target.value;
                if (v) {
                  const d = new Date(v + "T12:00:00");
                  const day = Math.min(28, Math.max(1, d.getDate()));
                  setPayday(day);
                  setValue("murabaha.payday", day);
                }
              },
            })}
            type="date"
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          />
        </Field>

        <Field label="День платежа (1–28) *" error={errors.murabaha?.payday?.message}>
          <input
            type="number"
            min={1}
            max={28}
            value={payday}
            onChange={(e) => {
              const v = Math.min(28, Math.max(1, Number(e.target.value) || 1));
              setPayday(v);
              setValue("murabaha.payday", v);
            }}
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          />
        </Field>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Залог *" error={errors.murabaha?.pledge?.message}>
          <select
            value={pledge}
            onChange={(e) => {
              const v = e.target.value as "Да" | "Нет";
              setPledge(v);
              setValue("murabaha.pledge", v);
            }}
            className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          >
            <option value="Нет">Нет</option>
            <option value="Да">Да</option>
          </select>
        </Field>
      </div>

      {needsGuarantor && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 rounded-xl border border-amber-100 bg-amber-50/50 p-4">
          <Field label="ФИО поручителя *" error={errors.murabaha?.guarantor_name?.message}>
            <input
              {...register("murabaha.guarantor_name")}
              type="text"
              className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            />
          </Field>
          <Field label="Телефон поручителя *" error={errors.murabaha?.guarantor_phone?.message}>
            <input
              {...register("murabaha.guarantor_phone")}
              type="tel"
              className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            />
          </Field>
        </div>
      )}

      <div className="rounded-xl border bg-slate-50 p-4 space-y-2 text-sm">
        <p className="font-semibold text-[#1a3a5c]">Расчёт</p>
        {quoteLoading && <p className="text-gray-500">Считаем…</p>}
        {quote && !quoteLoading && (
          <>
            <p className="text-gray-600">
              Наценка: {formatCurrency(quote.markup)} ({quote.rate_per_month_pct}% в месяц)
            </p>
            <p className="text-gray-600">Итого: {formatCurrency(quote.total)}</p>
            <p className="text-gray-600">
              Взнос: {formatCurrency(quote.down_payment_amount)} ({quote.down_payment_pct}%)
            </p>
            <p className="font-medium text-[#1a3a5c]">
              Ежемесячный платёж: {formatCurrency(quote.monthly_payment)}
            </p>
          </>
        )}
        {!quote && !quoteLoading && amountNum > 0 && (
          <p className="text-gray-500">Укажите параметры для расчёта</p>
        )}
        {(errors.murabaha?.principal?.message || errors.murabaha?.markup?.message) && (
          <p className="text-red-500 text-xs">
            {errors.murabaha?.principal?.message ?? errors.murabaha?.markup?.message}
          </p>
        )}
      </div>
    </>
  );
}
