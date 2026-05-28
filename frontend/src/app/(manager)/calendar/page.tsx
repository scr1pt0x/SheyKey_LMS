"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate, formatCurrency } from "@/lib/utils";
import { CalendarDays, Plus, CheckCircle } from "lucide-react";
import Link from "next/link";

const TABS = ["Сегодня", "Неделя", "Задачи"] as const;
type Tab = (typeof TABS)[number];

export default function CalendarPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Сегодня");
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDate, setTaskDate] = useState(new Date().toISOString().slice(0, 10));
  const qc = useQueryClient();

  const todayPayments = useQuery({
    queryKey: ["calendar", "today"],
    queryFn: async () => {
      const { data } = await api.get("/api/calendar/today");
      return data;
    },
  });

  const weekPayments = useQuery({
    queryKey: ["calendar", "week"],
    queryFn: async () => {
      const { data } = await api.get("/api/calendar/week");
      return data;
    },
  });

  const tasks = useQuery({
    queryKey: ["calendar", "tasks"],
    queryFn: async () => {
      const { data } = await api.get("/api/calendar/tasks", { params: { status: "pending" } });
      return data;
    },
  });

  const createTask = useMutation({
    mutationFn: () =>
      api.post("/api/calendar/tasks", { title: taskTitle, due_date: taskDate }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["calendar", "tasks"] });
      setShowTaskForm(false);
      setTaskTitle("");
    },
  });

  const completeTask = useMutation({
    mutationFn: (id: string) => api.patch(`/api/calendar/tasks/${id}`, { status: "done" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calendar", "tasks"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <CalendarDays size={22} /> Мой календарь
        </h1>
        {activeTab === "Задачи" && (
          <Button size="sm" onClick={() => setShowTaskForm(!showTaskForm)}>
            <Plus size={16} /> Задача
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b flex gap-6">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-[#1a3a5c] text-[#1a3a5c]"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Сегодня" && (
        <div className="space-y-3">
          {todayPayments.isLoading ? (
            <div className="flex justify-center py-8"><div className="animate-spin h-6 w-6 border-2 border-[#1a3a5c] border-t-transparent rounded-full" /></div>
          ) : (todayPayments.data as unknown[])?.length === 0 ? (
            <div className="bg-white rounded-xl border p-8 text-center text-gray-500">
              На сегодня платежей нет
            </div>
          ) : (
            (todayPayments.data as { schedule_id: string; deal_id: string; due_date: string; amount: number }[])?.map((p) => (
              <div key={p.schedule_id} className="bg-white rounded-xl border p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">{formatDate(p.due_date)}</p>
                  <p className="text-2xl font-bold text-[#1a3a5c]">{formatCurrency(p.amount)}</p>
                </div>
                <Link href={`/deals/${p.deal_id}`}>
                  <Button size="sm" variant="outline">Открыть сделку →</Button>
                </Link>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "Неделя" && (
        <div className="space-y-2">
          {weekPayments.isLoading ? (
            <div className="flex justify-center py-8"><div className="animate-spin h-6 w-6 border-2 border-[#1a3a5c] border-t-transparent rounded-full" /></div>
          ) : (weekPayments.data as unknown[])?.length === 0 ? (
            <p className="text-center text-gray-500 py-8">На неделю платежей нет</p>
          ) : (
            (weekPayments.data as { schedule_id: string; deal_id: string; due_date: string; amount: number }[])?.map((p) => (
              <div key={p.schedule_id} className="bg-white rounded-xl border p-3 flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-500">{formatDate(p.due_date)}</p>
                  <p className="font-semibold">{formatCurrency(p.amount)}</p>
                </div>
                <Link href={`/deals/${p.deal_id}`}>
                  <Button size="sm" variant="ghost">→</Button>
                </Link>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "Задачи" && (
        <div className="space-y-3">
          {showTaskForm && (
            <div className="bg-white rounded-xl border p-4 space-y-3">
              <input
                type="text"
                value={taskTitle}
                onChange={(e) => setTaskTitle(e.target.value)}
                placeholder="Название задачи..."
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              />
              <input
                type="date"
                value={taskDate}
                onChange={(e) => setTaskDate(e.target.value)}
                className="w-full px-3 py-2.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
              />
              <div className="flex gap-2">
                <Button size="sm" loading={createTask.isPending} onClick={() => createTask.mutate()}>Добавить</Button>
                <Button size="sm" variant="outline" onClick={() => setShowTaskForm(false)}>Отмена</Button>
              </div>
            </div>
          )}

          {tasks.isLoading ? (
            <div className="flex justify-center py-8"><div className="animate-spin h-6 w-6 border-2 border-[#1a3a5c] border-t-transparent rounded-full" /></div>
          ) : (tasks.data as unknown[])?.length === 0 ? (
            <p className="text-center text-gray-500 py-8">Задач нет</p>
          ) : (
            (tasks.data as { id: string; title: string; due_date: string; status: string }[])?.map((task) => (
              <div key={task.id} className="bg-white rounded-xl border p-4 flex items-center gap-3">
                <button
                  onClick={() => completeTask.mutate(task.id)}
                  className="text-gray-400 hover:text-green-600 transition-colors shrink-0"
                >
                  <CheckCircle size={20} />
                </button>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{task.title}</p>
                  <p className="text-xs text-gray-500">{formatDate(task.due_date)}</p>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
