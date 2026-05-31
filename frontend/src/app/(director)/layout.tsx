import { AppLayout } from "@/components/features/shared/AppLayout";
import { RequireRole } from "@/components/features/shared/RequireRole";

export default function DirectorLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole roles={["director"]}>
      <AppLayout>{children}</AppLayout>
    </RequireRole>
  );
}
