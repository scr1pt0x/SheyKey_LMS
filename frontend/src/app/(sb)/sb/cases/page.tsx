"use client";

import { Suspense } from "react";
import SbCasesContent from "./SbCasesContent";

export default function SbCasesPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-12">
          <div className="animate-spin h-8 w-8 border-2 border-[#1a3a5c] border-t-transparent rounded-full" />
        </div>
      }
    >
      <SbCasesContent />
    </Suspense>
  );
}
