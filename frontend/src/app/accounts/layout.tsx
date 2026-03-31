"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/ui/Sidebar";
import { useAuthStore } from "@/lib/auth";

export default function AccountsLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, fetchMe } = useAuthStore();
  useEffect(() => {
    if (!user) fetchMe().catch(() => router.replace("/auth/login"));
  }, [user, fetchMe, router]);
  if (!user) return null;
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  );
}
