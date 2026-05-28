"use client";

import { useToast } from "@/hooks/useToast";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

export function Toaster() {
  const { toasts, dismiss } = useToast();

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            "flex items-start gap-3 rounded-xl p-4 shadow-lg text-sm",
            "animate-in slide-in-from-right-5",
            toast.variant === "destructive"
              ? "bg-red-600 text-white"
              : "bg-[#1a3a5c] text-white"
          )}
        >
          <span className="flex-1">{toast.description ?? toast.title}</span>
          <button
            onClick={() => dismiss(toast.id)}
            className="shrink-0 opacity-70 hover:opacity-100"
          >
            <X size={16} />
          </button>
        </div>
      ))}
    </div>
  );
}
