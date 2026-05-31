import { AppLayout } from "@/components/features/shared/AppLayout";
import { RequireRole } from "@/components/features/shared/RequireRole";

export default function ManagerLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole roles={["manager", "director"]}>
      <AppLayout>{children}</AppLayout>
    </RequireRole>
  );
}
