"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/axios";
import { Search } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";

interface SearchClientHit {
  id: string;
  full_name: string;
  phone: string | null;
  cases: { case_id: string | null; sb_user_id?: string | null }[];
}

type Variant = "sidebar" | "light" | "page";

interface ClientSearchFieldProps {
  variant?: Variant;
  /** For page variant: only filter list, no navigation dropdown */
  listOnly?: boolean;
  value?: string;
  onChange?: (value: string) => void;
  className?: string;
}

export function ClientSearchField({
  variant = "sidebar",
  listOnly = false,
  value: controlledValue,
  onChange,
  className,
}: ClientSearchFieldProps) {
  const [internalQ, setInternalQ] = useState("");
  const q = controlledValue ?? internalQ;
  const setQ = onChange ?? setInternalQ;
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const role = useAuthStore((s) => s.user?.role);

  const { data, isFetching } = useQuery({
    queryKey: ["search", q],
    queryFn: async () => {
      const { data: res } = await api.get("/api/search", { params: { q } });
      return res as { hits: SearchClientHit[] };
    },
    enabled: !listOnly && q.trim().length >= 2,
  });

  useEffect(() => {
    if (listOnly) return;
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [listOnly]);

  const clientHref = (id: string) => (role === "sb" ? `/sb/clients/${id}` : `/clients/${id}`);
  const hits = data?.hits ?? [];

  const inputClass =
    variant === "sidebar"
      ? "w-full pl-9 pr-3 py-2 text-sm rounded-lg bg-white/10 text-white placeholder:text-white/50 border border-white/20 focus:outline-none focus:ring-2 focus:ring-white/30"
      : "w-full pl-9 pr-3 py-2.5 text-sm rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]";

  return (
    <div ref={ref} className={cn("relative w-full", className)}>
      <div className="relative">
        <Search
          size={16}
          className={cn(
            "absolute left-3 top-1/2 -translate-y-1/2",
            variant === "sidebar" ? "text-white/50" : "text-gray-400"
          )}
        />
        <input
          type="search"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            if (!listOnly) setOpen(true);
          }}
          onFocus={() => !listOnly && setOpen(true)}
          placeholder="Поиск по ФИО или телефону"
          className={inputClass}
        />
      </div>
      {!listOnly && open && q.length >= 2 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border z-[200] max-h-80 overflow-y-auto text-gray-900">
          {isFetching ? (
            <p className="p-3 text-sm text-gray-500">Поиск…</p>
          ) : hits.length === 0 ? (
            <p className="p-3 text-sm text-gray-500">Ничего не найдено</p>
          ) : (
            <div className="p-2">
              {hits.map((hit) => {
                const openCases = hit.cases.filter((c) => c.case_id);
                const hasUnassigned =
                  role === "sb" && openCases.some((c) => !c.sb_user_id);
                return (
                  <button
                    key={hit.id}
                    type="button"
                    className="w-full text-left px-2 py-2 text-sm hover:bg-gray-50 rounded"
                    onClick={() => {
                      router.push(clientHref(hit.id));
                      setOpen(false);
                      setQ("");
                    }}
                  >
                    <span className="font-medium">{hit.full_name}</span>
                    {hit.phone ? (
                      <span className="text-gray-400 ml-1">{hit.phone}</span>
                    ) : null}
                    <p className="text-xs text-gray-500 mt-0.5">
                      {role === "sb"
                        ? `${openCases.length} дел в СБ`
                        : `${hit.cases.length} рассрочек`}
                      {hasUnassigned ? " · есть неназначенные" : ""}
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
