"use client";

import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { Upload, FileText, ExternalLink, Loader2 } from "lucide-react";
import { toast } from "@/hooks/useToast";
import { getErrorMessage } from "@/lib/axios";

interface DocumentItem {
  id: string;
  file_name: string;
  file_url: string;
  doc_type: string;
  uploaded_by: string;
  created_at: string;
}

const DOC_TYPE_LABELS: Record<string, string> = {
  contract: "Договор",
  collateral: "Залог",
  photo: "Фото",
  receipt: "Чек",
  act: "Акт",
  notification: "Уведомление",
  other: "Другое",
};

const DOC_TYPE_COLORS: Record<string, string> = {
  contract: "bg-blue-100 text-blue-800",
  collateral: "bg-purple-100 text-purple-800",
  photo: "bg-green-100 text-green-800",
  receipt: "bg-yellow-100 text-yellow-800",
  act: "bg-orange-100 text-orange-800",
  notification: "bg-gray-100 text-gray-700",
  other: "bg-gray-100 text-gray-700",
};

interface Props {
  entityType: "deal" | "overdue_case" | "client" | "payment";
  entityId: string;
  availableDocTypes?: string[];
}

const DEFAULT_DOC_TYPES = ["contract", "collateral", "photo", "receipt", "other"];
const SB_DOC_TYPES = ["act", "notification", "photo", "other"];

export function DocumentsSection({ entityType, entityId, availableDocTypes }: Props) {
  const [uploading, setUploading] = useState(false);
  const [selectedDocType, setSelectedDocType] = useState(
    (availableDocTypes ?? DEFAULT_DOC_TYPES)[0]
  );
  const fileInputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const docTypes = availableDocTypes ?? (entityType === "overdue_case" ? SB_DOC_TYPES : DEFAULT_DOC_TYPES);

  const { data, isLoading } = useQuery({
    queryKey: ["documents", entityType, entityId],
    queryFn: async () => {
      const { data } = await api.get("/api/documents", {
        params: { entity_type: entityType, entity_id: entityId },
      });
      return data as { items: DocumentItem[]; total: number };
    },
  });

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      // Step 1: Get presigned URL
      const { data: presigned } = await api.post("/api/documents/presigned-url", {
        entity_type: entityType,
        entity_id: entityId,
        doc_type: selectedDocType,
        file_name: file.name,
        content_type: file.type || "application/octet-stream",
      });

      // Step 2: Upload directly to MinIO
      await fetch(presigned.upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type || "application/octet-stream" },
      });

      // Step 3: Confirm upload to API
      await api.post("/api/documents/confirm", {
        object_key: presigned.object_key,
        entity_type: entityType,
        entity_id: entityId,
        doc_type: selectedDocType,
        file_name: file.name,
        file_size: file.size,
      });

      toast({ title: "Файл загружен", description: file.name });
      qc.invalidateQueries({ queryKey: ["documents", entityType, entityId] });
    } catch (err) {
      toast({ title: "Ошибка загрузки", description: getErrorMessage(err), variant: "destructive" });
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-4">
      {/* Upload area */}
      <div className="bg-white rounded-xl border p-4 space-y-3">
        <div className="flex items-center gap-3 flex-wrap">
          <select
            value={selectedDocType}
            onChange={(e) => setSelectedDocType(e.target.value)}
            className="pl-3 pr-9 py-2 min-w-[9rem] text-sm border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#1a3a5c]"
          >
            {docTypes.map((t) => (
              <option key={t} value={t}>{DOC_TYPE_LABELS[t] ?? t}</option>
            ))}
          </select>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
            accept="image/*,.pdf,.doc,.docx,.xls,.xlsx"
          />
          <Button
            size="sm"
            variant="outline"
            loading={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
            Загрузить файл
          </Button>
        </div>
        <p className="text-xs text-gray-400">Поддерживаются: изображения, PDF, Word, Excel (макс. 50 МБ)</p>
      </div>

      {/* Documents list */}
      {isLoading ? (
        <p className="text-center text-gray-500 text-sm py-4">Загрузка...</p>
      ) : !data?.items.length ? (
        <p className="text-center text-gray-500 text-sm py-4">Документов нет</p>
      ) : (
        <div className="space-y-2">
          {data.items.map((doc) => (
            <div key={doc.id} className="flex items-center gap-3 bg-white rounded-xl border p-3">
              <FileText size={20} className="text-gray-400 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{doc.file_name}</p>
                <p className="text-xs text-gray-500">{formatDate(doc.created_at)}</p>
              </div>
              <Badge className={DOC_TYPE_COLORS[doc.doc_type] ?? "bg-gray-100 text-gray-700"}>
                {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
              </Badge>
              <a
                href={doc.file_url}
                target="_blank"
                rel="noreferrer"
                className="text-[#1a3a5c] hover:text-[#0f2744] shrink-0"
              >
                <ExternalLink size={16} />
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
