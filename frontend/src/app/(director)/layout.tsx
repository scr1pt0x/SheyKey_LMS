import { AppLayout } from "@/components/features/shared/AppLayout";

export default function DirectorLayout({ children }: { children: React.ReactNode }) {
  return <AppLayout>{children}</AppLayout>;
}
