"use client";

import Image from "next/image";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(username, password);
      router.push("/midias");
    } catch {
      setError("Usuário ou senha incorretos.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-oppi-bg px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="relative mx-auto mb-4 h-20 w-20 overflow-hidden rounded-full border border-oppi-border bg-white">
            <Image src="/logo-oppi.svg" alt="Oppi" fill className="object-cover" priority />
          </div>
          <h1 className="text-3xl font-black text-oppi-navy">Oppi</h1>
          <p className="mt-1 text-sm text-slate-500">Acesse o dashboard</p>
        </div>

        <form onSubmit={handleSubmit} className="filter-card space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-600">Usuário</label>
            <input
              className="input-field"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Digite seu usuário"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-600">Senha</label>
            <input
              type="password"
              className="input-field"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Digite sua senha"
              required
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-slate-400">Acesso restrito</p>
      </div>
    </div>
  );
}
