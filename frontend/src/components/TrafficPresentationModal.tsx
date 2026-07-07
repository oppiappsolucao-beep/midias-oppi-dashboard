"use client";

import type { TrafficForm } from "@/lib/api";

interface TrafficPresentationModalProps {
  open: boolean;
  values: TrafficForm;
  onClose: () => void;
  onNew: () => void;
  onDownload: () => void;
}

export function TrafficPresentationModal({
  open,
  values,
  onClose,
  onNew,
  onDownload,
}: TrafficPresentationModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded-2xl bg-white p-6 shadow-2xl">
        <div className="text-xs font-black uppercase tracking-widest text-oppi-magenta">Oppi Tech</div>
        <h2 className="mt-2 text-3xl font-black text-oppi-navy">Apresentação de resultados</h2>
        <div className="my-4 h-1 w-16 rounded-full bg-gradient-to-r from-oppi-purple to-oppi-magenta" />

        <div className="space-y-3 text-base leading-relaxed text-oppi-slate">
          <p>Bom dia, estes são os resultados dos anúncios.</p>
          <p>
            A empresa <strong>{values.empresa}</strong> realizou uma campanha na plataforma{" "}
            <strong>{values.plataforma}</strong>.
          </p>
          <p>
            A campanha apresentada é <strong>{values.campanha}</strong>.
          </p>
          <p>
            O período analisado foi de <strong>{values.periodo_inicio}</strong> até{" "}
            <strong>{values.periodo_fim}</strong>.
          </p>
          <p>
            Durante esse período, foram investidos <strong>R$ {values.investimento}</strong> em anúncios.
          </p>
          <p>
            O custo médio por dia foi de <strong>R$ {values.custo_dia}</strong>.
          </p>
          <p>
            A campanha alcançou <strong>{values.alcance}</strong> pessoas e recebeu{" "}
            <strong>{values.visualizacoes}</strong> visualizações.
          </p>
          <p>
            Foram gerados <strong>{values.contatos}</strong> contatos, com um custo médio de{" "}
            <strong>R$ {values.custo_contato}</strong> por contato.
          </p>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <button className="btn-primary" onClick={onDownload}>
            Baixar PDF com a logo da Oppi
          </button>
          <button className="btn-secondary" onClick={onClose}>
            Voltar para editar
          </button>
          <button className="btn-secondary" onClick={onNew}>
            Nova apresentação
          </button>
        </div>
      </div>
    </div>
  );
}
