"use client";

import { useState } from "react";
import { useExpenses, useExpensesTotal, useCreateExpense, useDeleteExpense } from "@/hooks/useProfit";
import { expenseCreateSchema, type ExpenseCreateForm } from "@/lib/schemas/profit";
import { Button } from "@/components/ui/button";
import { formatCurrency, formatDate } from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { Receipt, Plus, Trash2 } from "lucide-react";

const CATEGORY_OPTIONS = [
  { value: "cost_of_goods", label: "Себестоимость" },
  { value: "operational", label: "Операционные расходы" },
  { value: "salary", label: "Зарплаты" },
  { value: "rent", label: "Аренда" },
  { value: "other", label: "Прочее" },
];

const CATEGORY_COLORS: Record<string, string> = {
  cost_of_goods: "bg-blue-100 text-blue-800",
  operational: "bg-purple-100 text-purple-800",
  salary: "bg-green-100 text-green-800",
  rent: "bg-orange-100 text-orange-800",
  other: "bg-gray-100 text-gray-700",
};

export default function ExpensesPage() {
  const now = new Date();
  const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
  const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);

  const [dateFrom, setDateFrom] = useState(firstDay);
  const [dateTo, setDateTo] = useState(lastDay);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ category: "operational", amount: "", description: "", expense_date: now.toISOString().slice(0, 10) });

  const { data: expenses, isLoading } = useExpenses(dateFrom, dateTo);
  const { data: totals } = useExpensesTotal(dateFrom, dateTo);
  const createExpense = useCreateExpense();
  const deleteExpense = useDeleteExpense();

  function handleCreate() {
    const parsed = expenseCreateSchema.safeParse({
      category: form.category as ExpenseCreateForm["category"],
      amount: parseFloat(form.amount),
      description: form.description.trim() || undefined,
      expense_date: form.expense_date,
    });
    if (!parsed.success) {
      toast({ title: "Проверьте форму", description: parsed.error.errors[0]?.message, variant: "destructive" });
      return;
    }
    createExpense.mutate(parsed.data, {
      onSuccess: () => { toast({ title: "Расход добавлен" }); setShowForm(false); setForm({ ...form, amount: "", description: "" }); },
      onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
    });
  }

  return (
    <div className="space-y-5 w-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Receipt size={22} className="text-[#1a3a5c]" />
          <h1 className="text-xl font-bold">Расходы</h1>
        </div>
        <Button size="sm" onClick={() => setShowForm(!showForm)}>
          <Plus size={16} /> Добавить расход
        </Button>
      </div>

      {/* Date filter */}
      <div className="bg-white rounded-xl border p-4 flex gap-3 flex-wrap items-center">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">С:</span>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="px-2 py-1.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">По:</span>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="px-2 py-1.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
        </div>
        {totals && (
          <span className="ml-auto font-bold text-[#1a3a5c]">
            Итого: {formatCurrency(totals.total)}
          </span>
        )}
      </div>

      {/* Totals by category */}
      {totals && Object.keys(totals.by_category).length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {Object.entries(totals.by_category).map(([cat, amount]) => (
            <div key={cat} className="bg-white rounded-xl border p-3">
              <p className="text-xs text-gray-500 truncate">{cat}</p>
              <p className="font-bold">{formatCurrency(amount)}</p>
            </div>
          ))}
        </div>
      )}

      {/* Add form */}
      {showForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h2 className="font-semibold">Новый расход</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Категория *</label>
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]">
                {CATEGORY_OPTIONS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Сумма (₽) *</label>
              <input type="number" step="100" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" placeholder="50000" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Дата *</label>
              <input type="date" value={form.expense_date} onChange={(e) => setForm({ ...form, expense_date: e.target.value })} className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Описание</label>
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]" placeholder="Аренда офиса за май" />
            </div>
          </div>
          <div className="flex gap-3">
            <Button size="sm" loading={createExpense.isPending} disabled={!form.amount} onClick={handleCreate}>Добавить</Button>
            <Button size="sm" variant="outline" onClick={() => setShowForm(false)}>Отмена</Button>
          </div>
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-8"><div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" /></div>
      ) : (
        <div className="bg-white rounded-xl border overflow-hidden">
          {expenses?.length === 0 ? (
            <p className="text-center text-gray-500 py-8">Расходов за период нет</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Дата</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Категория</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600 hidden sm:table-cell">Описание</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Сумма</th>
                  <th />
                </tr>
              </thead>
              <tbody className="divide-y">
                {expenses?.map((exp) => (
                  <tr key={exp.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(exp.expense_date)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${CATEGORY_COLORS[exp.category] ?? "bg-gray-100 text-gray-700"}`}>
                        {exp.category_label}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell text-gray-500 text-xs">{exp.description || "—"}</td>
                    <td className="px-4 py-3 font-semibold">{formatCurrency(exp.amount)}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() =>
                          deleteExpense.mutate(exp.id, {
                            onSuccess: () => toast({ title: "Расход удалён" }),
                            onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
                          })
                        }
                        className="text-gray-400 hover:text-red-500"
                      >
                        <Trash2 size={15} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
