"use client";

import { useDeal } from "@/hooks/useDeals";
import { DealPaymentPanel } from "./DealPaymentPanel";
import { X } from "lucide-react";

const PAYABLE_STATUSES = new Set(["active", "overdue"]);

interface RecordPaymentDialogProps {
  dealId: string | null;
  clientName?: string | null;
  onClose: () => void;
  onRecorded?: () => void;
}

export function RecordPaymentDialog({
  dealId,
  clientName,
  onClose,
  onRecorded,
}: RecordPaymentDialogProps) {
  const { data: deal, isLoading } = useDeal(dealId ?? "", !!dealId);

  if (!dealId) return null;

  const canRecord = deal ? PAYABLE_STATUSES.has(deal.status) : false;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-gray-50 rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-gray-50 border-b px-4 py-3 flex items-center justify-between">
          <h2 className="font-semibold">Принять платёж</h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-200"
            aria-label="Закрыть"
          >
            <X size={20} />
          </button>
        </div>
        <div className="p-4">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
            </div>
          ) : deal ? (
            <>
              <p className="text-sm text-gray-600 mb-4">
                {clientName && <span className="font-medium">{clientName}</span>}
                {clientName && " · "}
                {deal.purchase_summary ?? deal.total}
              </p>
              <DealPaymentPanel
                dealId={dealId}
                schedules={deal.payment_schedules ?? []}
                canRecord={canRecord}
                onRecorded={() => {
                  onRecorded?.();
                  onClose();
                }}
              />
            </>
          ) : (
            <p className="text-sm text-gray-500 py-4">Сделка не найдена</p>
          )}
        </div>
      </div>
    </div>
  );
}
