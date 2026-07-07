"use client";

import { useState } from "react";
import { DashboardLayout } from "@/components/DashboardLayout";
import { TrafficPresentationModal } from "@/components/TrafficPresentationModal";
import {
  downloadTrafficPdf,
  validateTrafficForm,
  type TrafficForm,
} from "@/lib/api";
import { formatDateInput } from "@/lib/utils";
import { useAuthGuard } from "@/lib/useAuthGuard";

const emptyForm: TrafficForm = {
  empresa: "",
  campanha: "",
  plataforma: "",
  periodo_inicio: "",
  periodo_fim: "",
  investimento: "",
  custo_dia: "",
  alcance: "",
  visualizacoes: "",
  contatos: "",
  custo_contato: "",
};

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-600">{label}</label>
      <input
        type={type}
        className="input-field"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

export default function TrafegoPage() {
  const ready = useAuthGuard();
  const [form, setForm] = useState<TrafficForm>(emptyForm);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);

  function updateField(key: keyof TrafficForm, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function updateDateField(key: "periodo_inicio" | "periodo_fim", isoValue: string) {
    updateField(key, formatDateInput(isoValue));
  }

  async function handleOpenPresentation() {
    setError("");
    try {
      const validation = await validateTrafficForm(form);
      if (!validation.valid) {
        if (validation.missing.length) {
          setError(`Preencha todos os campos. Faltando: ${validation.missing.join(", ")}.`);
        } else {
          setError(validation.error || "Formulário inválido.");
        }
        return;
      }
      setShowModal(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao validar formulário.");
    }
  }

  if (!ready) return null;

  return (
    <DashboardLayout title="Apresentação de resultados" subtitle="Resultados dos anúncios">
      <div className="traffic-card space-y-8">
        <div>
          <h2 className="text-2xl font-black text-oppi-navy">Apresentação de resultados</h2>
          <p className="mt-1 text-sm text-slate-500">
            Preencha os dados da campanha e abra a apresentação para gerar uma tela pronta para print.
          </p>
        </div>

        <section className="space-y-4">
          <div>
            <h3 className="font-bold">📌 Identificação da campanha</h3>
            <p className="text-sm text-slate-500">Informe para qual cliente e campanha os resultados serão apresentados.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <Field label="Empresa" value={form.empresa} onChange={(v) => updateField("empresa", v)} placeholder="Nome da empresa" />
            <Field label="Nome da campanha" value={form.campanha} onChange={(v) => updateField("campanha", v)} placeholder="Ex.: Campanha Junho" />
            <Field label="Plataforma" value={form.plataforma} onChange={(v) => updateField("plataforma", v)} placeholder="Ex.: Meta Ads" />
          </div>
        </section>

        <section className="space-y-4">
          <div>
            <h3 className="font-bold">📅 Período analisado</h3>
            <p className="text-sm text-slate-500">Selecione as datas pelo calendário.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-600">Data inicial</label>
              <input type="date" className="input-field" onChange={(e) => updateDateField("periodo_inicio", e.target.value)} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-600">Data final</label>
              <input type="date" className="input-field" onChange={(e) => updateDateField("periodo_fim", e.target.value)} />
            </div>
          </div>
        </section>

        <section className="space-y-4">
          <div>
            <h3 className="font-bold">💰 Investimento</h3>
            <p className="text-sm text-slate-500">Preencha os valores da campanha no período selecionado.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Valor investido em anúncios" value={form.investimento} onChange={(v) => updateField("investimento", v)} placeholder="Ex.: 2.500,00" />
            <Field label="Custo médio por dia" value={form.custo_dia} onChange={(v) => updateField("custo_dia", v)} placeholder="Ex.: 100,00" />
          </div>
        </section>

        <section className="space-y-4">
          <div>
            <h3 className="font-bold">📊 Resultados dos anúncios</h3>
            <p className="text-sm text-slate-500">Informe os principais indicadores entregues pela campanha.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Field label="Pessoas alcançadas" value={form.alcance} onChange={(v) => updateField("alcance", v)} placeholder="Ex.: 15.000" />
            <Field label="Visualizações" value={form.visualizacoes} onChange={(v) => updateField("visualizacoes", v)} placeholder="Ex.: 25.000" />
            <Field label="Contatos gerados" value={form.contatos} onChange={(v) => updateField("contatos", v)} placeholder="Ex.: 120" />
            <Field label="Custo médio por contato" value={form.custo_contato} onChange={(v) => updateField("custo_contato", v)} placeholder="Ex.: 12,50" />
          </div>
        </section>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button className="btn-primary w-full max-w-md" onClick={handleOpenPresentation}>
          Abrir apresentação
        </button>
      </div>

      <TrafficPresentationModal
        open={showModal}
        values={form}
        onClose={() => setShowModal(false)}
        onNew={() => {
          setForm(emptyForm);
          setShowModal(false);
        }}
        onDownload={() => downloadTrafficPdf(form)}
      />
    </DashboardLayout>
  );
}
