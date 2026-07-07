"use client";

import { useState } from "react";
import type { MediaRow } from "@/lib/api";
import { updateRowStatus, updateRowTema } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

interface MediaRowCardProps {
  row: MediaRow;
  onUpdated: () => void;
}

const STATUS_OPTIONS = ["Pronto", "Em andamento", "Pausado", "Pendente"];

export function MediaRowCard({ row, onUpdated }: MediaRowCardProps) {
  const [tema, setTema] = useState(row.tema);
  const [loading, setLoading] = useState(false);

  async function handleSaveTema() {
    setLoading(true);
    try {
      await updateRowTema(row.row_index, tema);
      onUpdated();
    } finally {
      setLoading(false);
    }
  }

  async function handleStatus(status: string) {
    setLoading(true);
    try {
      await updateRowStatus(row.row_index, status);
      onUpdated();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-oppi-border bg-slate-50/70 p-4">
      <div className="grid gap-4 lg:grid-cols-[1.4fr_0.5fr_1.6fr]">
        <div>
          <div className="text-lg font-bold text-oppi-navy">{row.tema}</div>
          <div className="mt-1 text-sm text-slate-600">
            <b>Empresa:</b> {row.empresa} &nbsp; <b>Mês:</b> {row.mes} &nbsp; <b>Semana:</b> {row.semana}
          </div>
          <div className="mt-1 text-sm text-slate-600">
            <b>Tipo de arte:</b> {row.tipo_arte} &nbsp; <b>Data:</b> {row.data}
          </div>
          <div className="mt-3 flex gap-2">
            <input
              className="input-field"
              value={tema}
              onChange={(e) => setTema(e.target.value)}
              placeholder="Editar nome da atividade"
            />
            <button className="btn-secondary shrink-0" onClick={handleSaveTema} disabled={loading}>
              Salvar nome
            </button>
          </div>
        </div>

        <div>
          <div className="text-sm text-slate-500">Valor</div>
          <div className="text-xl font-bold text-oppi-navy">{row.valor_fmt}</div>
        </div>

        <div>
          <div className="mb-2 text-sm font-semibold">Status atual</div>
          <StatusBadge status={row.status_arte} />
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {STATUS_OPTIONS.map((status) => (
              <button
                key={status}
                className="btn-status"
                disabled={loading}
                onClick={() => handleStatus(status)}
              >
                {status}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
