"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useSbPromisesCalendar } from "@/hooks/useSb";
import { formatCurrency, formatDate } from "@/lib/utils";
import { CalendarDays } from "lucide-react";

export default function SbPromisesPage() {
  const today = new Date();
  const weekEnd = new Date(today);
  weekEnd.setDate(weekEnd.getDate() + 13);

  const [dateFrom, setDateFrom] = useState(today.toISOString().slice(0, 10));
  const [dateTo, setDateTo] = useState(weekEnd.toISOString().slice(0, 10));

  const { data: promises = [], isLoading } = useSbPromisesCalendar(dateFrom, dateTo);

  const byDate = useMemo(() => {
    const map = new Map<string, typeof promises>();
    for (const p of promises) {
      const list = map.get(p.promised_date) ?? [];
      list.push(p);
      map.set(p.promised_date, list);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [promises]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold flex items-center gap-2">
        <CalendarDays size={22} className="text-[#1a3a5c]" /> Календарь обещаний
      </h1>

      <div className="bg-white rounded-xl border p-4 flex flex-wrap gap-3">
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="px-3 py-2 text-sm border rounded-lg" />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="px-3 py-2 text-sm border rounded-lg" />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : byDate.length === 0 ? (
        <p className="text-gray-500 text-sm">Нет обещаний в выбранном периоде</p>
      ) : (
        <div className="space-y-4">
          {byDate.map(([date, items]) => (
            <div key={date} className="bg-white rounded-xl border p-4">
              <p className="font-semibold text-sm mb-2">{formatDate(date)}</p>
              <ul className="space-y-2">
                {items.map((p) => (
                  <li key={p.promise_id}>
                    <Link href={`/sb/cases/${p.case_id}`} className="flex justify-between text-sm hover:bg-gray-50 rounded p-2 -mx-2">
                      <span>{formatCurrency(p.promised_amount)}</span>
                      <span className="text-gray-500">долг {formatCurrency(p.total_debt)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
