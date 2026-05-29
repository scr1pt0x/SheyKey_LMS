"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell } from "lucide-react";
import { cn, formatDateTime } from "@/lib/utils";
import {
  useUnreadCount,
  useNotificationInbox,
  useMarkRead,
  useMarkAllRead,
} from "@/hooks/useNotifications";

export function NotificationBell({
  direction = "down",
  side = "right",
}: {
  direction?: "up" | "down";
  side?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  const { data: countData } = useUnreadCount();
  const { data: inboxData, refetch } = useNotificationInbox();
  const markRead = useMarkRead();
  const markAllRead = useMarkAllRead();

  const unread = countData?.count ?? 0;
  const notifications = inboxData?.items ?? [];

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  function handleOpen() {
    setOpen((v) => !v);
    if (!open) refetch();
  }

  function handleClickNotification(n: { id: string; action_url: string | null; is_read: boolean }) {
    if (!n.is_read) {
      markRead.mutate(n.id);
    }
    setOpen(false);
    if (n.action_url) {
      router.push(n.action_url);
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={handleOpen}
        className="relative flex items-center justify-center w-10 h-10 rounded-lg hover:bg-white/10 transition-colors"
        aria-label="Уведомления"
      >
        <Bell size={20} className="text-white" />
        {unread > 0 && (
          <span className="absolute top-1.5 right-1.5 flex items-center justify-center w-4 h-4 bg-red-500 rounded-full text-[10px] font-bold text-white leading-none">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className={`absolute w-80 bg-white rounded-xl shadow-2xl border z-50 overflow-hidden ${
          direction === "up" ? "bottom-full mb-2" : "top-full mt-2"
        } ${
          side === "right" ? "left-0" : "right-0"
        }`}>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
            <span className="font-semibold text-sm text-gray-800">Уведомления</span>
            {unread > 0 && (
              <button
                onClick={() => markAllRead.mutate()}
                className="text-xs text-[#1a3a5c] hover:underline"
              >
                Прочитать все
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto divide-y">
            {notifications.length === 0 ? (
              <p className="text-center text-sm text-gray-500 py-8">Нет уведомлений</p>
            ) : (
              notifications.map((n) => (
                <button
                  key={n.id}
                  onClick={() => handleClickNotification(n)}
                  className={cn(
                    "w-full text-left px-4 py-3 transition-colors hover:bg-gray-50",
                    !n.is_read && "bg-blue-50"
                  )}
                >
                  <div className="flex items-start gap-2">
                    {!n.is_read && (
                      <span className="mt-1.5 shrink-0 w-2 h-2 rounded-full bg-blue-500" />
                    )}
                    <div className={cn("flex-1 min-w-0", n.is_read && "ml-4")}>
                      <p className="text-sm font-medium text-gray-900 truncate">{n.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.body}</p>
                      <p className="text-[11px] text-gray-400 mt-1">
                        {formatDateTime(n.created_at)}
                      </p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
