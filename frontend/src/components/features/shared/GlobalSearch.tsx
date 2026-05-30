"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/axios";
import { Search } from "lucide-react";
import { useAuthStore } from "@/store/auth";

export function GlobalSearch() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const role = useAuthStore((s) => s.user?.role);

  const { data } = useQuery({
    queryKey: ["search", q],
    queryFn: async () => {
      const { data: res } = await api.get("/api/search", { params: { q } });
      return res as {
        clients: { id: string; full_name: string; phone: string | null }[];
        deals: { id: string; client_id: string; type: string; status: string; total: number }[];
      };
    },
    enabled: q.trim().length >= 2,
  });

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const clientHref = (id: string) =>
    role === "director" ? `/clients/${id}` : `/clients/${id}`;
  const dealHref = (id: string) => `/deals/${id}`;

  return (
    <div ref={ref} className="relative hidden md:block flex-1 max-w-xs">
      <div className="relative">
        <Search size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-white/50" />
        <input
          type="search"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Поиск клиента или сделки…"
          className="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg bg-white/10 text-white placeholder:text-white/50 border border-white/20 focus:outline-none focus:ring-2 focus:ring-white/30"
        />
      </div>
      {open && q.length >= 2 && data && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border z-50 max-h-80 overflow-y-auto text-gray-900">
          {data.clients.length === 0 && data.deals.length === 0 ? (
            <p className="p-3 text-sm text-gray-500">Ничего не найдено</p>
          ) : (
            <>
              {data.clients.length > 0 && (
                <div className="p-2">
                  <p className="text-xs font-medium text-gray-400 px-2 py-1">Клиенты</p>
                  {data.clients.map((c) => (
                    <button
                      key={c.id}
                      type="button"
                      className="w-full text-left px-2 py-2 text-sm hover:bg-gray-50 rounded"
                      onClick={() => {
                        router.push(clientHref(c.id));
                        setOpen(false);
                        setQ("");
                      }}
                    >
                      {c.full_name}
                      {c.phone ? <span className="text-gray-400 ml-1">{c.phone}</span> : null}
                    </button>
                  ))}
                </div>
              )}
              {data.deals.length > 0 && (
                <div className="p-2 border-t">
                  <p className="text-xs font-medium text-gray-400 px-2 py-1">Сделки</p>
                  {data.deals.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      className="w-full text-left px-2 py-2 text-sm hover:bg-gray-50 rounded"
                      onClick={() => {
                        router.push(dealHref(d.id));
                        setOpen(false);
                        setQ("");
                      }}
                    >
                      {d.type} · {d.status} · {d.total.toLocaleString("ru-RU")} ₽
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
