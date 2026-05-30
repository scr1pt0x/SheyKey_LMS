"use client";

import { useMemo, useState } from "react";
import {
  useInvestors,
  useInvestorSummary,
  useCreateInvestor,
  useUpdateInvestor,
  useDeactivateInvestor,
  type Investor,
} from "@/hooks/useProfit";
import { investorCreateSchema, investorUpdateSchema } from "@/lib/schemas/profit";
import { Button } from "@/components/ui/button";
import { formatCurrency, formatDate } from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { Users, Plus, Pencil, X, TrendingUp } from "lucide-react";

const EMPTY_FORM = {
  name: "",
  phone: "",
  investment_amount: "",
  joined_at: new Date().toISOString().slice(0, 10),
  notes: "",
};

export default function InvestorsPage() {
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);

  const { data: investors, isLoading } = useInvestors();
  const { data: summary } = useInvestorSummary();
  const createInvestor = useCreateInvestor();
  const deactivate = useDeactivateInvestor();

  const updateInvestor = useUpdateInvestor(editId ?? "");

  const editingInvestor = investors?.find((i) => i.id === editId);

  const previewSharePct = useMemo(() => {
    const amount = parseFloat(form.investment_amount);
    if (!amount || amount <= 0 || !summary) return null;
    const baseTotal = summary.total_invested - (editingInvestor?.investment_amount ?? 0);
    const newTotal = baseTotal + amount;
    if (newTotal <= 0) return null;
    return Math.round((amount / newTotal) * 10000) / 100;
  }, [form.investment_amount, summary, editingInvestor]);

  function openCreate() {
    setEditId(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(inv: Investor) {
    setEditId(inv.id);
    setForm({
      name: inv.name,
      phone: inv.phone ?? "",
      investment_amount: inv.investment_amount ? String(inv.investment_amount) : "",
      joined_at: inv.joined_at ?? new Date().toISOString().slice(0, 10),
      notes: inv.notes ?? "",
    });
    setShowForm(true);
  }

  function handleSubmit() {
    const investmentAmount = parseFloat(form.investment_amount);

    if (editId) {
      const raw = {
        name: form.name.trim(),
        phone: form.phone.trim() || null,
        investment_amount: Number.isFinite(investmentAmount) ? investmentAmount : undefined,
        joined_at: form.joined_at || null,
        notes: form.notes.trim() || null,
      };
      const parsed = investorUpdateSchema.safeParse(raw);
      if (!parsed.success) {
        toast({ title: "Проверьте форму", description: parsed.error.errors[0]?.message, variant: "destructive" });
        return;
      }
      updateInvestor.mutate(parsed.data, {
        onSuccess: () => { toast({ title: "Инвестор обновлён" }); setShowForm(false); },
        onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
      });
    } else {
      const raw = {
        name: form.name.trim(),
        phone: form.phone.trim() || null,
        investment_amount: investmentAmount,
        joined_at: form.joined_at || null,
        notes: form.notes.trim() || null,
      };
      const parsed = investorCreateSchema.safeParse(raw);
      if (!parsed.success) {
        toast({ title: "Проверьте форму", description: parsed.error.errors[0]?.message, variant: "destructive" });
        return;
      }
      createInvestor.mutate(parsed.data, {
        onSuccess: () => { toast({ title: "Инвестор добавлен" }); setShowForm(false); },
        onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
      });
    }
  }

  const totalShare = summary?.total_share_pct ?? 0;
  const partnerRemainder = summary?.partner_remainder_pct ?? 0;

  return (
    <div className="space-y-5 max-w-3xl">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users size={22} className="text-[#1a3a5c]" />
          <h1 className="text-xl font-bold">Инвесторы</h1>
        </div>
        <Button size="sm" onClick={openCreate}>
          <Plus size={16} /> Добавить инвестора
        </Button>
      </div>

      {summary && (
        <div className="bg-white rounded-xl border p-5 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Распределено долей (авто)</span>
            <span className="font-bold text-lg">{totalShare}%</span>
          </div>
          <div className="w-full bg-gray-100 rounded-full h-3 overflow-hidden">
            <div
              className="h-3 rounded-full bg-[#1a3a5c] transition-all"
              style={{ width: `${Math.min(totalShare, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>Инвесторы: {totalShare}%</span>
            <span>Остаток партнёрам: {partnerRemainder}%</span>
          </div>
          {summary.total_invested > 0 && (
            <p className="text-sm text-gray-600">
              Общая сумма вложений:{" "}
              <span className="font-semibold">{formatCurrency(summary.total_invested)}</span>
            </p>
          )}
        </div>
      )}

      {showForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h2 className="font-semibold">{editId ? "Редактировать инвестора" : "Новый инвестор"}</h2>
          <p className="text-sm text-gray-500">
            Доля в прибыли рассчитывается автоматически: вложение ÷ сумма всех вложений × 100%.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="ФИО *">
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input" placeholder="Алибек Жаксыбеков" />
            </Field>
            <Field label="Телефон">
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="input" placeholder="+79001234567" />
            </Field>
            <Field label="Сумма вложения (₽) *">
              <input type="number" step="1000" min="1" value={form.investment_amount} onChange={(e) => setForm({ ...form, investment_amount: e.target.value })} className="input" placeholder="2000000" />
            </Field>
            <Field label="Доля (расчётная)">
              <div className="input bg-gray-50 text-[#1a3a5c] font-semibold flex items-center gap-1">
                <TrendingUp size={16} />
                {previewSharePct != null ? `${previewSharePct}%` : "—"}
              </div>
            </Field>
            <Field label="Дата входа">
              <input type="date" value={form.joined_at} onChange={(e) => setForm({ ...form, joined_at: e.target.value })} className="input" />
            </Field>
          </div>
          <Field label="Заметки">
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} className="input resize-none" />
          </Field>
          <div className="flex gap-3">
            <Button size="sm" loading={createInvestor.isPending || updateInvestor.isPending} onClick={handleSubmit} disabled={!form.name || !form.investment_amount}>
              {editId ? "Сохранить" : "Добавить"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>Отмена</Button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-8"><div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" /></div>
      ) : (
        <div className="space-y-3">
          {investors?.map((inv) => (
            <div key={inv.id} className="bg-white rounded-xl border p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-lg">{inv.name}</p>
                  {inv.phone && <p className="text-sm text-gray-500">{inv.phone}</p>}
                  <div className="flex items-center gap-4 mt-2 flex-wrap">
                    <span className="flex items-center gap-1 text-[#1a3a5c] font-bold text-xl">
                      <TrendingUp size={18} />{inv.share_pct}%
                    </span>
                    {inv.investment_amount != null && (
                      <span className="text-sm text-gray-600">Вложено: <strong>{formatCurrency(inv.investment_amount)}</strong></span>
                    )}
                    {inv.joined_at && (
                      <span className="text-xs text-gray-500">с {formatDate(inv.joined_at)}</span>
                    )}
                  </div>
                  {inv.notes && <p className="text-xs text-gray-500 mt-1">{inv.notes}</p>}
                </div>
                <div className="flex gap-2 shrink-0 ml-3">
                  <button onClick={() => openEdit(inv)} className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-[#1a3a5c]">
                    <Pencil size={16} />
                  </button>
                  <button
                    onClick={() =>
                      deactivate.mutate(inv.id, {
                        onSuccess: () => toast({ title: "Инвестор деактивирован" }),
                        onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
                      })
                    }
                    className="p-2 rounded-lg hover:bg-red-50 text-gray-500 hover:text-red-600"
                  >
                    <X size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))}
          {!investors?.length && (
            <div className="bg-white rounded-xl border p-8 text-center text-gray-500">
              Инвесторов нет. Добавьте первого инвестора.
            </div>
          )}
        </div>
      )}

      <style jsx>{`
        .input {
          width: 100%;
          padding: 0.625rem 0.75rem;
          font-size: 0.875rem;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          outline: none;
        }
        .input:focus { box-shadow: 0 0 0 2px #1a3a5c40; border-color: #1a3a5c; }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  );
}
