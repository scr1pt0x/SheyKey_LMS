"use client";

import { useRef, useState } from "react";
import api from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";
import { Upload, FileSpreadsheet, CheckCircle, AlertTriangle, ChevronRight } from "lucide-react";

type Step = "upload" | "preview" | "result";

interface PreviewData {
  headers: string[];
  column_map: Record<string, number>;
  preview_rows: Record<string, string>[];
  total_rows: number;
  detected_fields: string[];
  missing_required: string[];
}

interface ImportResult {
  imported: number;
  skipped_duplicate: number;
  skipped_no_name: number;
  skipped_no_phone: number;
  errors: string[];
  manager_id: string | null;
}

const FIELD_LABELS: Record<string, string> = {
  full_name: "ФИО",
  phone: "Телефон",
  passport: "Паспорт",
  address: "Адрес",
};

export default function ImportPage() {
  const [step, setStep] = useState<Step>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function handleFile(f: File) {
    setFile(f);
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", f);
      const { data } = await api.post("/api/director/import/preview", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setPreview(data as PreviewData);
      setStep("preview");
    } catch (err) {
      toast({ title: "Ошибка разбора файла", description: getErrorMessage(err), variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }

  async function handleImport() {
    if (!file) return;
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post("/api/director/import/clients", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(data as ImportResult);
      setStep("result");
    } catch (err) {
      toast({ title: "Ошибка импорта", description: getErrorMessage(err), variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setStep("upload");
    setFile(null);
    setPreview(null);
    setResult(null);
    if (fileRef.current) fileRef.current.value = "";
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-2">
        <FileSpreadsheet size={22} className="text-[#1a3a5c]" />
        <h1 className="text-xl font-bold">Импорт клиентов из таблицы</h1>
      </div>

      {/* Instruction */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800 space-y-1">
        <p className="font-semibold">Как подготовить файл из Google Таблиц:</p>
        <ol className="list-decimal list-inside space-y-0.5 text-blue-700">
          <li>Открой таблицу с клиентами в Google Sheets</li>
          <li>Файл → Скачать → <strong>Microsoft Excel (.xlsx)</strong> или <strong>CSV</strong></li>
          <li>Загрузи полученный файл ниже</li>
        </ol>
        <p className="text-xs text-blue-600 mt-2">
          Система автоматически распознаёт колонки: ФИО, Телефон, Паспорт, Адрес — на русском и английском.
        </p>
      </div>

      {/* Steps breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        {(["upload", "preview", "result"] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <span className={`font-medium ${step === s ? "text-[#1a3a5c]" : "text-gray-400"}`}>
              {i + 1}. {s === "upload" ? "Загрузка" : s === "preview" ? "Проверка" : "Результат"}
            </span>
            {i < 2 && <ChevronRight size={14} className="text-gray-300" />}
          </div>
        ))}
      </div>

      {/* ── Step 1: Upload ───────────────────────────────────────────────────── */}
      {step === "upload" && (
        <div
          className="bg-white rounded-xl border-2 border-dashed border-gray-300 hover:border-[#1a3a5c] transition-colors p-12 text-center cursor-pointer"
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const f = e.dataTransfer.files[0];
            if (f) handleFile(f);
          }}
        >
          <Upload size={40} className="mx-auto text-gray-400 mb-3" />
          <p className="font-medium text-gray-700">Перетащи файл сюда или нажми для выбора</p>
          <p className="text-sm text-gray-500 mt-1">Поддерживается: .xlsx, .csv</p>
          <input
            ref={fileRef}
            type="file"
            accept=".xlsx,.xls,.csv"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
          {loading && (
            <div className="mt-4 flex justify-center">
              <div className="animate-spin h-6 w-6 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
            </div>
          )}
        </div>
      )}

      {/* ── Step 2: Preview ─────────────────────────────────────────────────── */}
      {step === "preview" && preview && (
        <div className="space-y-4">
          {/* Column detection */}
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold mb-3">Распознанные колонки</h2>
            <div className="flex flex-wrap gap-2 mb-3">
              {Object.entries(preview.column_map).map(([field, idx]) => (
                <div key={field} className="flex items-center gap-1.5 bg-green-50 border border-green-200 rounded-lg px-3 py-1.5">
                  <CheckCircle size={14} className="text-green-600" />
                  <span className="text-sm font-medium">{FIELD_LABELS[field] ?? field}</span>
                  <span className="text-xs text-gray-500">← «{preview.headers[idx]}»</span>
                </div>
              ))}
            </div>
            {preview.missing_required.length > 0 && (
              <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 rounded-lg p-3">
                <AlertTriangle size={16} />
                <span>
                  Не найдены обязательные колонки: {preview.missing_required.map((f) => FIELD_LABELS[f] ?? f).join(", ")}.
                  Проверьте заголовки таблицы.
                </span>
              </div>
            )}
          </div>

          {/* Preview table */}
          <div className="bg-white rounded-xl border overflow-hidden">
            <div className="p-4 border-b flex items-center justify-between">
              <h2 className="font-semibold">
                Предпросмотр — первые {preview.preview_rows.length} строк из {preview.total_rows}
              </h2>
              <Badge className="bg-[#1a3a5c]/10 text-[#1a3a5c]">
                Всего строк: {preview.total_rows}
              </Badge>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    {Object.keys(preview.column_map).map((field) => (
                      <th key={field} className="text-left px-4 py-2 font-medium text-gray-600">
                        {FIELD_LABELS[field] ?? field}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {preview.preview_rows.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      {Object.keys(preview.column_map).map((field) => (
                        <td key={field} className="px-4 py-2 text-gray-700">
                          {row[field] || <span className="text-gray-400">—</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              loading={loading}
              disabled={preview.missing_required.length > 0}
              onClick={handleImport}
            >
              Импортировать {preview.total_rows} клиентов
            </Button>
            <Button variant="outline" onClick={reset}>Отмена</Button>
          </div>
        </div>
      )}

      {/* ── Step 3: Result ──────────────────────────────────────────────────── */}
      {step === "result" && result && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border p-6 space-y-4">
            <div className="flex items-center gap-3">
              <CheckCircle size={28} className="text-green-600" />
              <h2 className="text-xl font-bold">Импорт завершён</h2>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <Stat label="Импортировано" value={result.imported} color="green" />
              <Stat label="Дубли пропущены" value={result.skipped_duplicate} color="yellow" />
              <Stat label="Нет имени" value={result.skipped_no_name} color="gray" />
              <Stat label="Нет телефона" value={result.skipped_no_phone} color="gray" />
            </div>

            {result.errors.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="font-medium text-red-700 mb-2">Ошибки ({result.errors.length}):</p>
                <ul className="text-sm text-red-600 space-y-0.5">
                  {result.errors.map((e, i) => <li key={i}>• {e}</li>)}
                </ul>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <Button onClick={reset}>Импортировать ещё один файл</Button>
            <Button variant="outline" onClick={() => window.location.href = "/clients"}>
              Перейти к клиентам →
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  const colors: Record<string, string> = {
    green: "bg-green-50 text-green-700",
    yellow: "bg-yellow-50 text-yellow-700",
    gray: "bg-gray-50 text-gray-600",
  };
  return (
    <div className={`rounded-xl p-4 text-center ${colors[color]}`}>
      <p className="text-3xl font-bold">{value}</p>
      <p className="text-xs mt-1">{label}</p>
    </div>
  );
}
