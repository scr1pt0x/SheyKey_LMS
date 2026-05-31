"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/axios";
import { useAuthStore } from "@/store/auth";
import { cn, ROLE_LABELS } from "@/lib/utils";
import { NotificationBell } from "./NotificationBell";
import { ClientSearchField } from "./ClientSearchField";
import {
  Users,
  FileText,
  Calendar,
  Shield,
  BarChart2,
  Settings,
  LogOut,
  AlertTriangle,
  CheckSquare,
  Home,
  MoreHorizontal,
  X,
  Upload,
  TrendingUp,
  Receipt,
  Users2,
  UserCog,
  User,
  Search,
} from "lucide-react";
import { useState } from "react";

type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  roles: string[];
  /** Show in mobile bottom bar (max 3 per role + "More") */
  primary?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  // Director
  { href: "/director/dashboard",  label: "Дашборд",       icon: Home,        roles: ["director"], primary: true },
  { href: "/director/approval",   label: "Согласование",  icon: CheckSquare, roles: ["director"], primary: true },
  { href: "/director/analytics",  label: "Аналитика",     icon: BarChart2,   roles: ["director"], primary: true },
  { href: "/director/sb-control",  label: "Контроль СБ",   icon: Shield,      roles: ["director"] },
  { href: "/director/team",       label: "Команда",       icon: Users,       roles: ["director"] },
  { href: "/director/staff",      label: "Сотрудники",    icon: UserCog,     roles: ["director"] },
  { href: "/director/reports",    label: "Отчёты",        icon: FileText,    roles: ["director"] },
  { href: "/director/audit",      label: "Аудит",         icon: Shield,      roles: ["director"] },
  { href: "/director/settings",   label: "Настройки",     icon: Settings,    roles: ["director"] },
  { href: "/director/import",     label: "Импорт данных", icon: Upload,      roles: ["director"] },
  { href: "/director/profit",     label: "Прибыль",       icon: TrendingUp,  roles: ["director"], primary: true },
  { href: "/director/investors",  label: "Инвесторы",     icon: Users2,      roles: ["director"] },
  { href: "/director/expenses",   label: "Расходы",       icon: Receipt,     roles: ["director"] },
  { href: "/clients",             label: "Клиенты",       icon: Users,       roles: ["director"] },
  { href: "/deals",               label: "Сделки",        icon: FileText,    roles: ["director"] },
  // Manager
  { href: "/dashboard",           label: "Дашборд",       icon: Home,        roles: ["manager"], primary: true },
  { href: "/clients",             label: "Клиенты",       icon: Users,       roles: ["manager"], primary: true },
  { href: "/deals",               label: "Сделки",        icon: FileText,    roles: ["manager"], primary: true },
  { href: "/calendar",            label: "Календарь",     icon: Calendar,    roles: ["manager"], primary: true },
  // SB
  { href: "/sb/dashboard",        label: "Дашборд",       icon: Home,        roles: ["sb"], primary: true },
  { href: "/sb/cases",            label: "Просрочники",   icon: AlertTriangle, roles: ["sb"], primary: true },
  { href: "/sb/stats",            label: "Моя работа",    icon: BarChart2,   roles: ["sb"] },
  { href: "/sb/promises",         label: "Обещания",      icon: Calendar,    roles: ["sb"] },
  { href: "/profile",             label: "Профиль",       icon: User,        roles: ["manager", "sb", "director"] },
];

export function AppLayout({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const router = useRouter();
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);

  const { mutate: doLogout } = useMutation({
    mutationFn: () => api.post("/api/auth/logout"),
    onSettled: () => {
      logout();
      router.replace("/login");
    },
  });

  if (!user) return null;

  const roleItems = NAV_ITEMS.filter((item) => item.roles.includes(user.role));
  const primaryItems = roleItems.filter((item) => item.primary);
  const moreItems = roleItems.filter((item) => !item.primary);

  return (
    <div className="min-h-screen bg-gray-50 flex">

      {/* ── Desktop Sidebar (md+) ─────────────────────────────────────── */}
      <aside className="hidden md:flex flex-col w-64 bg-[#1a3a5c] text-white shrink-0">
        <div className="p-5 border-b border-white/10">
          <p className="font-bold text-lg">SheyKey LMS</p>
          <p className="text-xs text-white/60 mt-0.5">{ROLE_LABELS[user.role]}</p>
          <p className="text-sm font-medium mt-1">{user.name}</p>
        </div>

        <nav className="flex-1 py-4 overflow-y-auto">
          {roleItems.map((item) => (
            <Link
              key={item.href + item.label}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-5 py-3 text-sm transition-colors",
                pathname.startsWith(item.href)
                  ? "bg-white/15 font-semibold"
                  : "hover:bg-white/10 text-white/80"
              )}
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Bottom row: notifications + logout */}
        <div className="border-t border-white/10 p-3 flex items-center justify-between">
          <NotificationBell direction="up" side="right" />
          <button
            onClick={() => doLogout()}
            className="flex items-center gap-2 px-3 py-2 text-sm text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          >
            <LogOut size={18} />
            Выйти
          </button>
        </div>
      </aside>

      {/* ── Mobile Top Bar (< md) ─────────────────────────────────────── */}
      <div className="md:hidden fixed top-0 inset-x-0 z-40 bg-[#1a3a5c] text-white flex flex-col">
        <div className="flex items-center px-4 h-14 gap-3 shrink-0">
          <p className="font-bold flex-1 text-base truncate">SheyKey LMS</p>
          <NotificationBell />
        </div>
        {user.role === "sb" && (
          <div className="px-3 pb-2 overflow-visible">
            <ClientSearchField variant="sidebar" />
          </div>
        )}
      </div>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main
        className={cn(
          "flex-1 flex flex-col min-w-0 md:mt-0 mb-20 md:mb-0",
          user.role === "sb" ? "mt-[7.5rem] md:mt-0" : "mt-14"
        )}
      >
        <div className="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto">{children}</div>
      </main>

      {/* ── Mobile Bottom Nav (< md) ──────────────────────────────────── */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white border-t shadow-lg safe-area-inset-bottom">
        <div className="flex items-stretch h-16">
          {primaryItems.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href + item.label}
                href={item.href}
                className={cn(
                  "flex-1 flex flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors",
                  active ? "text-[#1a3a5c]" : "text-gray-500"
                )}
              >
                <item.icon size={22} className={active ? "text-[#1a3a5c]" : "text-gray-400"} />
                <span className="truncate max-w-[60px] text-center leading-tight">{item.label}</span>
              </Link>
            );
          })}

          {/* "More" tab — only if there are secondary items */}
          {moreItems.length > 0 && (
            <button
              onClick={() => setMoreOpen(true)}
              className="flex-1 flex flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-gray-500"
            >
              <MoreHorizontal size={22} className="text-gray-400" />
              <span>Ещё</span>
            </button>
          )}
        </div>
      </nav>

      {/* ── "More" bottom sheet ───────────────────────────────────────── */}
      {moreOpen && (
        <>
          {/* Overlay */}
          <div
            className="md:hidden fixed inset-0 z-50 bg-black/40"
            onClick={() => setMoreOpen(false)}
          />
          {/* Sheet */}
          <div className="md:hidden fixed bottom-0 inset-x-0 z-50 bg-white rounded-t-2xl shadow-2xl pb-safe">
            <div className="flex items-center justify-between px-5 pt-4 pb-2 border-b">
              <span className="font-semibold text-gray-800">Меню</span>
              <button onClick={() => setMoreOpen(false)} className="p-1 rounded-lg hover:bg-gray-100">
                <X size={20} className="text-gray-500" />
              </button>
            </div>
            <div className="py-2">
              {moreItems.map((item) => (
                <Link
                  key={item.href + item.label}
                  href={item.href}
                  onClick={() => setMoreOpen(false)}
                  className={cn(
                    "flex items-center gap-4 px-5 py-4 text-base transition-colors",
                    pathname.startsWith(item.href)
                      ? "text-[#1a3a5c] font-semibold bg-blue-50"
                      : "text-gray-700 hover:bg-gray-50"
                  )}
                >
                  <item.icon size={22} />
                  {item.label}
                </Link>
              ))}
              <button
                onClick={() => doLogout()}
                className="flex items-center gap-4 px-5 py-4 text-base text-red-600 w-full hover:bg-red-50"
              >
                <LogOut size={22} />
                Выйти
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
