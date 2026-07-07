"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

const navItems = [
  { href: "/midias", label: "Mídias", icon: "📱" },
  { href: "/trafego", label: "Gestão de Tráfego", icon: "📊" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col border-r border-oppi-border bg-white px-5 py-6">
      <div className="mb-8 flex items-center gap-3">
        <div className="relative h-12 w-12 overflow-hidden rounded-full border border-oppi-border bg-white">
          <Image src="/logo-oppi.svg" alt="Oppi" fill className="object-cover" />
        </div>
        <div>
          <div className="text-sm font-black tracking-wide text-oppi-navy">OPPI TECH</div>
          <div className="text-xs text-slate-500">Painel interno</div>
        </div>
      </div>

      <div className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400">Navegação</div>

      <nav className="flex flex-col gap-2">
        {navItems.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                active
                  ? "bg-gradient-to-r from-oppi-purple/10 to-oppi-magenta/10 text-oppi-purple"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {item.icon} {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto space-y-3">
        <button onClick={handleLogout} className="btn-secondary w-full">
          SAIR DA CONTA
        </button>
        <p className="text-xs text-slate-400">
          Use o menu lateral para alternar entre Mídias e Gestão de Tráfego.
        </p>
      </div>
    </aside>
  );
}
