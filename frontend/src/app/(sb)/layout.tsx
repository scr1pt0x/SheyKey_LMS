import { AppLayout } from "@/components/features/shared/AppLayout";

export default function SbLayout({ children }: { children: React.ReactNode }) {
  return <AppLayout>{children}</AppLayout>;
}
