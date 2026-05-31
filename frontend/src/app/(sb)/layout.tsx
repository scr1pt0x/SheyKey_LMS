import { AppLayout } from "@/components/features/shared/AppLayout";
import { RequireRole } from "@/components/features/shared/RequireRole";
import { SbPresenceHeartbeat } from "@/components/features/sb/SbPresenceHeartbeat";

export default function SbLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireRole roles={["sb"]}>
      <AppLayout>
        <SbPresenceHeartbeat />
        {children}
      </AppLayout>
    </RequireRole>
  );
}
