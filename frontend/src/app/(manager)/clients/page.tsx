"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useClients } from "@/hooks/useClients";
import { Button } from "@/components/ui/button";
import { formatDate, formatPhone, cn } from "@/lib/utils";
import { Search, Plus, Archive } from "lucide-react";

const LIMIT = 20;

export default function ClientsPage() {
  const searchParams = useSearchParams();
  const managerIdParam = searchParams.get("manager_id") ?? "";

  const [q, setQ] = useState("");
  const [isArchived, setIsArchived] = useState(false);
  const [offset, setOffset] = useState(0);

  const { data, isLoading, error } = useClients({
    q: q || undefined,
    manager_id: managerIdParam || undefined,
    scope: managerIdParam ? "all" : undefined,
    is_archived: isArchived,
    limit: LIMIT,
    offset,
  });

  const totalPages = data ? Math.ceil(data.total / LIMIT) : 0;
  const currentPage = Math.floor(offset / LIMIT) + 1;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-bold text-gray-900">Клиенты</h1>
        <Link href="/clients/new">
          <Button size="sm">
            <Plus size={16} />
            Добавить клиента
          </Button>
        </Link>
      </div>

      <div className="bg-white rounded-xl border p-4 space-y-3">
        <div className="flex gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Поиск по имени, телефону, паспорту..."
              value={q}
              onChange={(e) => { setQ(e.target.value); setOffset(0); }}
              className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
            />
          </div>
          <button
            onClick={() => setIsArchived(!isArchived)}
            className={cn(
              "flex items-center gap-2 px-3 py-2 text-sm border rounded-lg transition-colors",
              isArchived ? "bg-gray-100 text-gray-700 border-gray-400" : "hover:bg-gray-50"
            )}
          >
            <Archive size={16} />
            {isArchived ? "Архив" : "Активные"}
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      ) : error ? (
        <p className="text-red-500 text-center py-8">Ошибка загрузки</p>
      ) : (
        <>
          <div className="md:hidden space-y-2">
            {data?.items.map((client) => (
              <Link
                key={client.id}
                href={`/clients/${client.id}`}
                className="flex items-center gap-3 bg-white rounded-xl border p-4 hover:shadow-sm transition-shadow"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900 truncate">{client.full_name}</p>
                  <p className="text-sm text-gray-500 mt-0.5">{formatPhone(client.phone)}</p>
                </div>
                <span className="text-gray-400 shrink-0">›</span>
              </Link>
            ))}
            {data?.items.length === 0 && (
              <p className="text-center text-gray-500 py-8">Клиенты не найдены</p>
            )}
          </div>

          <div className="hidden md:block bg-white rounded-xl border overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">ФИО</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Телефон</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Паспорт</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-600">Добавлен</th>
                    <th />
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data?.items.map((client) => (
                    <tr key={client.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium">{client.full_name}</td>
                      <td className="px-4 py-3 text-gray-600">{formatPhone(client.phone)}</td>
                      <td className="px-4 py-3 text-gray-600">{client.passport || "—"}</td>
                      <td className="px-4 py-3 text-gray-500">{formatDate(client.created_at)}</td>
                      <td className="px-4 py-3">
                        <Link href={`/clients/${client.id}`} className="text-[#1a3a5c] hover:underline text-xs font-medium">
                          Открыть →
                        </Link>
                      </td>
                    </tr>
                  ))}
                  {data?.items.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                        Клиенты не найдены
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t bg-gray-50">
                <p className="text-sm text-gray-500">{data?.total} клиентов</p>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setOffset(Math.max(0, offset - LIMIT))} disabled={offset === 0}>Назад</Button>
                  <span className="flex items-center px-3 text-sm">{currentPage} / {totalPages}</span>
                  <Button size="sm" variant="outline" onClick={() => setOffset(offset + LIMIT)} disabled={offset + LIMIT >= (data?.total ?? 0)}>Далее</Button>
                </div>
              </div>
            )}
          </div>

          {totalPages > 1 && (
            <div className="md:hidden flex items-center justify-between pt-2">
              <Button size="sm" variant="outline" onClick={() => setOffset(Math.max(0, offset - LIMIT))} disabled={offset === 0}>Назад</Button>
              <span className="text-sm text-gray-500">{currentPage} / {totalPages}</span>
              <Button size="sm" variant="outline" onClick={() => setOffset(offset + LIMIT)} disabled={offset + LIMIT >= (data?.total ?? 0)}>Далее</Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
