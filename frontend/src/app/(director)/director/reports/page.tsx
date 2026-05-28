"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import api from "@/lib/axios";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { FileText, Download } from "lucide-react";

type ReportType = "portfolio" | "overdue";
type Format = "pdf" | "xlsx";

const REPORTS = [
  { type: "portfolio" as ReportType, label: "Портфель", description: "Сводка по всем активным сделкам" },
  { type: "overdue" as ReportType, label: "Просрочки", description: "Детализация по просроченным делам" },
];

export default function ReportsPage() {
  const [loading, setLoading] = useState<string | null>(null);

  const download = async (type: ReportType, fmt: Format) => {
    const key = `${type}-${fmt}`;
    setLoading(key);
    try {
      const response = await api.post(
        `/api/documents/generate/report/${type}?fmt=${fmt}`,
        {},
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(response.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `отчёт_${type}_${new Date().toISOString().slice(0, 10)}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast({ title: "Ошибка генерации отчёта", description: getErrorMessage(err), variant: "destructive" });
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <FileText size={22} className="text-[#1a3a5c]" />
        <h1 className="text-xl font-bold">Отчёты</h1>
      </div>

      <p className="text-sm text-gray-500">
        Еженедельные и ежемесячные отчёты отправляются автоматически на email руководителя.
        Здесь можно сформировать отчёт на текущий момент.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {REPORTS.map((report) => (
          <div key={report.type} className="bg-white rounded-xl border p-5 space-y-4">
            <div>
              <h2 className="font-semibold text-lg">{report.label}</h2>
              <p className="text-sm text-gray-500">{report.description}</p>
            </div>
            <div className="flex gap-3">
              <Button
                size="sm"
                loading={loading === `${report.type}-pdf`}
                onClick={() => download(report.type, "pdf")}
              >
                <Download size={16} /> PDF
              </Button>
              <Button
                size="sm"
                variant="outline"
                loading={loading === `${report.type}-xlsx`}
                onClick={() => download(report.type, "xlsx")}
              >
                <Download size={16} /> Excel
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
