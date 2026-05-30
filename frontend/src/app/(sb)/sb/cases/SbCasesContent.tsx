"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useOverdueCases, useTakeCase } from "@/hooks/useSb";
import { useAuthStore } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, OVERDUE_STATUS_LABELS } from "@/lib/utils";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { AlertTriangle } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  new: "bg-red-100 text-red-800",
  in_progress: "bg-yellow-100 text-yellow-800",
  agreed: "bg-blue-100 text-blue-800",
  closed: "bg-green-100 text-green-800",
};

const LIMIT = 20;

type QueueFilter = "all" | "unassigned" | "mine";

export default function SbCasesContent() {
  const searchParams = useSearchParams();
  const user = useAuthStore((s) => s.user);
  const [status, setStatus] = useState("");
  const [queue, setQueue] = useState<QueueFilter>("all");
  const [offset, setOffset] = useState(0);
  const [daysMin, setDaysMin] = useState("");
  const [daysMax, setDaysMax] = useState("");
  const [amountMin, setAmountMin] = useState("");
  const [amountMax, setAmountMax] = useState("");
  const [redZoneOnly, setRedZoneOnly] = useState(false);
  const takeCase = useTakeCase();

  useEffect(() => {
    if (searchParams.get("unassigned") === "1") {
      setQueue("unassigned");
      setOffset(0);
    }
  }, [searchParams]);

  const queryParams: Record<string, unknown> = {
    status: status || undefined,
    limit: LIMIT,
    offset,
    days_overdue_min: daysMin ? parseInt(daysMin, 10) : undefined,
    days_overdue_max: daysMax ? parseInt(daysMax, 10) : undefined,
    amount_min: amountMin ? parseFloat(amountMin) : undefined,
    amount_max: amountMax ? parseFloat(amountMax) : undefined,
    red_zone_only: redZoneOnly || undefined,
  };
  if (queue === "unassigned") {
    queryParams.unassigned = true;
  } else if (queue === "mine" && user?.id) {
    queryParams.sb_user_id = user.id;
  }

  const { data, isLoading } = useOverdueCases(queryParams);

  function handleTake(caseId: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    takeCase.mutate(caseId, {
      onSuccess: () => toast({ title: "Дело взято в работу" }),
      onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <AlertTriangle size={22} className="text-red-500" />
        <h1 className="text-xl font-bold">Просрочники</h1>
      </div>

      <div className="bg-white rounded-xl border p-4 flex flex-wrap gap-3">
        <div className="flex rounded-lg border overflow-hidden text-sm">
          {(
            [
              ["all", "Все"],
              ["unassigned", "Неназначенные"],
              ["mine", "Мои"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => { setQueue(value); setOffset(0); }}
              className={`px-3 py-2 ${queue === value ? "bg-[#1a3a5c] text-white" : "bg-white text-gray-600 hover:bg-gray-50"}`}
            >
              {label}
            </button>
          ))}
        </div>
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
        <input
          type="number"
          placeholder="Дней от"
          value={daysMin}
          onChange={(e) => { setDaysMin(e.target.value); setOffset(0); }}
          className="w-24 px-2 py-2 text-sm border rounded-lg"
        />
        <input
          type="number"
          placeholder="Дней до"
          value={daysMax}
          onChange={(e) => { setDaysMax(e.target.value); setOffset(0); }}
          className="w-24 px-2 py-2 text-sm border rounded-lg"
        />
        <input
          type="number"
          placeholder="Долг от"
          value={amountMin}
          onChange={(e) => { setAmountMin(e.target.value); setOffset(0); }}
          className="w-28 px-2 py-2 text-sm border rounded-lg"
        />
        <input
          type="number"
          placeholder="Долг до"
          value={amountMax}
          onChange={(e) => { setAmountMax(e.target.value); setOffset(0); }}
          className="w-28 px-2 py-2 text-sm border rounded-lg"
        />
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={redZoneOnly}
            onChange={(e) => { setRedZoneOnly(e.target.checked); setOffset(0); }}
            className="accent-[#1a3a5c]"
          />
          Красная зона
        </label>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : (
        <>
          <div className="md:hidden space-y-2">
            {data?.items.map((c) => (
              <div key={c.id} className="bg-white rounded-xl border p-4">
                <Link href={`/sb/cases/${c.id}`} className="block">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge className={STATUS_COLORS[c.status]}>
                      {OVERDUE_STATUS_LABELS[c.status]}
                    </Badge>
                    {c.is_red_zone && (
                      <span className="text-xs text-red-600 font-medium">Красная зона</span>
                    )}
                    {!c.sb_user_id && (
                      <span className="text-xs text-orange-600 font-medium">Не назначен</span>
                    )}
                  </div>
                  <p className="text-xl font-bold text-red-600 mt-1">{formatCurrency(c.total_debt)}</p>
                  <p className="text-sm text-gray-500">{c.days_overdue} дн. просрочки</p>
                </Link>
                {!c.sb_user_id && (
                  <Button
                    size="sm"
                    className="mt-3 w-full"
                    loading={takeCase.isPending}
                    onClick={(e) => handleTake(c.id, e)}
                  >
                    Взять в работу
                  </Button>
                )}
              </div>
            ))}
            {!data?.items.length && (
              <p className="text-center text-gray-500 py-8">Дел нет</p>
            )}
          </div>

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
                        {c.is_red_zone && (
                          <span className="ml-1 text-xs text-red-600">Красная</span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-semibold text-red-600">{formatCurrency(c.total_debt)}</td>
                      <td className="px-4 py-3 font-medium">{c.days_overdue} дн.</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{c.sb_user_id ? "Назначен" : "Не назначен"}</td>
                      <td className="px-4 py-3 flex gap-2 justify-end">
                        {!c.sb_user_id && (
                          <Button
                            size="sm"
                            variant="outline"
                            loading={takeCase.isPending}
                            onClick={() => takeCase.mutate(c.id, {
                              onSuccess: () => toast({ title: "Дело взято в работу" }),
                              onError: (err) => toast({ title: "Ошибка", description: getErrorMessage(err), variant: "destructive" }),
                            })}
                          >
                            Взять
                          </Button>
                        )}
                        <Link href={`/sb/cases/${c.id}`} className="text-[#1a3a5c] hover:underline text-xs font-medium py-2">
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

          {data && data.total > LIMIT && (
            <div className="md:hidden flex items-center justify-between pt-2">
              <Button size="sm" variant="outline" onClick={() => setOffset(Math.max(0, offset - LIMIT))} disabled={offset === 0}>Назад</Button>
              <span className="text-sm text-gray-500">{Math.floor(offset / LIMIT) + 1} / {Math.ceil(data.total / LIMIT)}</span>
              <Button size="sm" variant="outline" onClick={() => setOffset(offset + LIMIT)} disabled={offset + LIMIT >= data.total}>Далее</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
