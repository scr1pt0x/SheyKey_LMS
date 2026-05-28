"use client";

import { useState } from "react";
import Link from "next/link";
import { useOverdueCases } from "@/hooks/useSb";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, OVERDUE_STATUS_LABELS } from "@/lib/utils";
import { AlertTriangle } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  new: "bg-red-100 text-red-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  agreed: "bg-blue-100 text-blue-800",
  closed: "bg-green-100 text-green-800",
};

const LIMIT = 20;

export default function SbCasesPage() {
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);

  const { data, isLoading } = useOverdueCases({
    status: status || undefined,
    limit: LIMIT,
    offset,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <AlertTriangle size={22} className="text-red-500" />
        <h1 className="text-xl font-bold">Просрочники</h1>
      </div>

      <div className="bg-white rounded-xl border p-4">
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setOffset(0); }}
          className="px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
        >
          <option value="">Все статусы</option>
          {Object.entries(OVERDUE_STATUS_LABELS).map(([v, l]) => (
            <option key={v} value={v}>{l}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : (
        <>
          {/* ── Mobile cards ──────────────────────────────────────────── */}
          <div className="md:hidden space-y-2">
            {data?.items.map((c) => (
              <Link
                key={c.id}
                href={`/sb/cases/${c.id}`}
                className="flex items-center gap-3 bg-white rounded-xl border p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className={STATUS_COLORS[c.status]}>
                      {OVERDUE_STATUS_LABELS[c.status]}
                    </Badge>
                    {!c.sb_user_id && (
                      <span className="text-xs text-orange-600 font-medium">Не назначен</span>
                    )}
                  </div>
                  <p className="text-xl font-bold text-red-600 mt-1">{formatCurrency(c.total_debt)}</p>
                  <p className="text-sm text-gray-500">{c.days_overdue} дн. просрочки</p>
                </div>
                <span className="text-gray-400 shrink-0">›</span>
              </Link>
            ))}
            {!data?.items.length && (
              <p className="text-center text-gray-500 py-8">Дел нет</p>
            )}
          </div>

          {/* ── Desktop table ─────────────────────────────────────────── */}
          <div className="hidden md:block bg-white rounded-xl border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Статус</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Долг</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Дней просрочки</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Назначен</th>
                    <th />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data?.items.map((c) => (
                    <tr key={c.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <Badge className={STATUS_COLORS[c.status]}>{OVERDUE_STATUS_LABELS[c.status]}</Badge>
                      </td>
                      <td className="px-4 py-3 font-semibold text-red-600">{formatCurrency(c.total_debt)}</td>
                      <td className="px-4 py-3 font-medium">{c.days_overdue} дн.</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{c.sb_user_id ? "Назначен" : "Не назначен"}</td>
                      <td className="px-4 py-3">
                        <Link href={`/sb/cases/${c.id}`} className="text-[#1a3a5c] hover:underline text-xs font-medium">
                          Открыть →
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {!data?.items.length && (
                    <tr><td colSpan={5} className="text-center py-8 text-gray-500">Дел нет</td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {data && data.total > LIMIT && (
              <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
                <p className="text-sm text-gray-500">{data.total} дел</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setOffset(Math.max(0, offset - LIMIT))} disabled={offset === 0}>Назад</Button>
                  <Button size="sm" variant="outline" onClick={() => setOffset(offset + LIMIT)} disabled={offset + LIMIT >= data.total}>Далее</Button>
                </div>
              </div>
            )}
          </div>

          {/* Mobile pagination */}
          {data && data.total > LIMIT && (
            <div className="md:hidden flex items-center justify-between pt-2">
              <Button size="sm" variant="outline" onClick={() => setOffset(Math.max(0, offset - LIMIT))} disabled={offset === 0}>Назад</Button>
              <span className="text-sm text-gray-500">{Math.floor(offset/LIMIT)+1} / {Math.ceil(data.total/LIMIT)}</span>
              <Button size="sm" variant="outline" onClick={() => setOffset(offset + LIMIT)} disabled={offset + LIMIT >= data.total}>Далее</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
