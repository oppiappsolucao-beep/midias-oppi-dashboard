import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";

export function DashboardLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-auto px-6 py-8 lg:px-10">
        <div className="mx-auto max-w-6xl">
          <div className="mb-2 text-center">
            <div className="mx-auto mb-3 h-16 w-16 overflow-hidden rounded-full border border-oppi-border bg-white">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo-oppi.svg" alt="Oppi" className="h-full w-full object-cover" />
            </div>
            <h1 className="text-3xl font-black text-oppi-navy">Dashboard — Oppi</h1>
            <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          </div>
          <div className="mb-6 text-lg font-bold text-oppi-navy">{title}</div>
          {children}
        </div>
      </main>
    </div>
  );
}
